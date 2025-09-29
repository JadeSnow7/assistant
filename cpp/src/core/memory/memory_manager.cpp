#include "../../include/nex/core/memory_manager.hpp"
#include "../../include/nex/platform_config.h"

#ifdef HUSHELL_HAS_CUDA
#include <cuda_runtime.h>
#include <cublas_v2.h>
#endif

#include <algorithm>
#include <cassert>
#include <cstring>

namespace hushell::core::memory {

    // ==================== GPUMemoryPool 实现 ====================

    class GPUMemoryPool::Impl {
    public:
        Impl() : initialized_(false) {
            initialize();
        }

        ~Impl() {
            cleanup();
        }

        void* allocate_gpu(size_t size, size_t alignment) {
            if (!initialized_) {
                return nullptr;
            }

            std::lock_guard<std::mutex> lock(mutex_);

            #ifdef HUSHELL_HAS_CUDA
            void* ptr = nullptr;
            cudaError_t result = cudaMalloc(&ptr, size);
            if (result == cudaSuccess) {
                allocated_blocks_[ptr] = size;
                stats_.gpu_total_allocated += size;
                stats_.gpu_current_usage += size;
                stats_.gpu_peak_usage = std::max(stats_.gpu_peak_usage, stats_.gpu_current_usage);
                return ptr;
            }
            #endif

            return nullptr;
        }

        void deallocate_gpu(void* ptr) {
            if (!ptr || !initialized_) {
                return;
            }

            std::lock_guard<std::mutex> lock(mutex_);

            auto it = allocated_blocks_.find(ptr);
            if (it != allocated_blocks_.end()) {
                size_t size = it->second;
                allocated_blocks_.erase(it);
                stats_.gpu_current_usage -= size;

                #ifdef HUSHELL_HAS_CUDA
                cudaFree(ptr);
                #endif
            }
        }

        MemoryStats get_gpu_stats() const {
            std::lock_guard<std::mutex> lock(mutex_);
            return stats_;
        }

        bool is_gpu_memory_available() const {
            return initialized_;
        }

        void cleanup() {
            if (!initialized_) {
                return;
            }

            std::lock_guard<std::mutex> lock(mutex_);

            // 清理所有未释放的GPU内存
            for (auto& [ptr, size] : allocated_blocks_) {
                #ifdef HUSHELL_HAS_CUDA
                cudaFree(ptr);
                #endif
            }
            allocated_blocks_.clear();

            #ifdef HUSHELL_HAS_CUDA
            cudaDeviceReset();
            #endif

            initialized_ = false;
        }

    private:
        void initialize() {
            #ifdef HUSHELL_HAS_CUDA
            int device_count = 0;
            cudaError_t result = cudaGetDeviceCount(&device_count);
            if (result == cudaSuccess && device_count > 0) {
                initialized_ = true;
            }
            #endif
        }

        mutable std::mutex mutex_;
        std::unordered_map<void*, size_t> allocated_blocks_;
        MemoryStats stats_;
        std::atomic<bool> initialized_;
    };

    GPUMemoryPool::GPUMemoryPool() : pimpl_(std::make_unique<Impl>()) {}
    GPUMemoryPool::~GPUMemoryPool() = default;

    void* GPUMemoryPool::allocate_gpu(size_t size, size_t alignment) {
        return pimpl_->allocate_gpu(size, alignment);
    }

    void GPUMemoryPool::deallocate_gpu(void* ptr) {
        pimpl_->deallocate_gpu(ptr);
    }

    MemoryStats GPUMemoryPool::get_gpu_stats() const {
        return pimpl_->get_gpu_stats();
    }

    bool GPUMemoryPool::is_gpu_memory_available() const {
        return pimpl_->is_gpu_memory_available();
    }

    void GPUMemoryPool::cleanup() {
        pimpl_->cleanup();
    }

    // ==================== MemoryMapper 实现 ====================

    MemoryMapper::~MemoryMapper() {
        std::lock_guard<std::mutex> lock(mutex_);
        for (auto& [addr, size] : mapped_regions_) {
            unmap_file(addr, size);
        }
    }

    void* MemoryMapper::map_file(const std::filesystem::path& path, size_t size, bool read_only) {
        std::lock_guard<std::mutex> lock(mutex_);

        #ifdef HUSHELL_PLATFORM_WINDOWS
        HANDLE file_handle = CreateFileW(
            path.wstring().c_str(),
            read_only ? GENERIC_READ : GENERIC_READ | GENERIC_WRITE,
            FILE_SHARE_READ,
            nullptr,
            OPEN_EXISTING,
            FILE_ATTRIBUTE_NORMAL,
            nullptr
        );

        if (file_handle == INVALID_HANDLE_VALUE) {
            return nullptr;
        }

        LARGE_INTEGER file_size;
        if (!GetFileSizeEx(file_handle, &file_size)) {
            CloseHandle(file_handle);
            return nullptr;
        }

        size_t map_size = (size == 0) ? static_cast<size_t>(file_size.QuadPart) : size;

        HANDLE mapping_handle = CreateFileMappingW(
            file_handle,
            nullptr,
            read_only ? PAGE_READONLY : PAGE_READWRITE,
            0, 0,
            nullptr
        );

        CloseHandle(file_handle);

        if (mapping_handle == nullptr) {
            return nullptr;
        }

        void* mapped_addr = MapViewOfFile(
            mapping_handle,
            read_only ? FILE_MAP_READ : FILE_MAP_WRITE,
            0, 0,
            map_size
        );

        CloseHandle(mapping_handle);

        if (mapped_addr != nullptr) {
            mapped_regions_[mapped_addr] = map_size;
        }

        return mapped_addr;

        #else // Unix系统
        int fd = open(path.c_str(), read_only ? O_RDONLY : O_RDWR);
        if (fd == -1) {
            return nullptr;
        }

        if (size == 0) {
            struct stat st;
            if (fstat(fd, &st) == -1) {
                close(fd);
                return nullptr;
            }
            size = st.st_size;
        }

        void* mapped_addr = mmap(
            nullptr,
            size,
            read_only ? PROT_READ : PROT_READ | PROT_WRITE,
            MAP_SHARED,
            fd,
            0
        );

        close(fd);

        if (mapped_addr == MAP_FAILED) {
            return nullptr;
        }

        mapped_regions_[mapped_addr] = size;
        return mapped_addr;
        #endif
    }

    void MemoryMapper::unmap_file(void* addr, size_t size) {
        if (!addr) {
            return;
        }

        #ifdef HUSHELL_PLATFORM_WINDOWS
        UnmapViewOfFile(addr);
        #else
        munmap(addr, size);
        #endif

        std::lock_guard<std::mutex> lock(mutex_);
        mapped_regions_.erase(addr);
    }

    void* MemoryMapper::map_anonymous(size_t size, bool executable) {
        std::lock_guard<std::mutex> lock(mutex_);

        #ifdef HUSHELL_PLATFORM_WINDOWS
        DWORD protect = executable ? PAGE_EXECUTE_READWRITE : PAGE_READWRITE;
        void* mapped_addr = VirtualAlloc(nullptr, size, MEM_COMMIT | MEM_RESERVE, protect);
        #else
        int prot = PROT_READ | PROT_WRITE;
        if (executable) {
            prot |= PROT_EXEC;
        }
        void* mapped_addr = mmap(nullptr, size, prot, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
        if (mapped_addr == MAP_FAILED) {
            mapped_addr = nullptr;
        }
        #endif

        if (mapped_addr) {
            mapped_regions_[mapped_addr] = size;
        }

        return mapped_addr;
    }

    size_t MemoryMapper::get_page_size() {
        #ifdef HUSHELL_PLATFORM_WINDOWS
        SYSTEM_INFO si;
        GetSystemInfo(&si);
        return si.dwPageSize;
        #else
        return getpagesize();
        #endif
    }

    size_t MemoryMapper::get_large_page_size() {
        #ifdef HUSHELL_PLATFORM_WINDOWS
        return GetLargePageMinimum();
        #elif defined(HUSHELL_HAS_HUGEPAGES)
        // Linux huge pages
        std::ifstream meminfo("/proc/meminfo");
        std::string line;
        while (std::getline(meminfo, line)) {
            if (line.find("Hugepagesize:") == 0) {
                size_t size_kb = std::stoull(line.substr(13));
                return size_kb * 1024;
            }
        }
        #endif
        return get_page_size();
    }

    // ==================== HighPerformanceAllocator 实现 ====================

    class HighPerformanceAllocator::Impl {
    public:
        explicit Impl(size_t pool_size) : pool_size_(pool_size), allocated_size_(0) {
            initialize_pool();
        }

        ~Impl() {
            cleanup_pool();
        }

        void* allocate(size_t size, size_t alignment) {
            std::lock_guard<std::mutex> lock(mutex_);

            // 对齐处理
            size_t aligned_size = (size + alignment - 1) & ~(alignment - 1);

            // 在空闲块中查找合适的内存
            for (auto it = free_blocks_.begin(); it != free_blocks_.end(); ++it) {
                if (it->size >= aligned_size) {
                    void* ptr = it->ptr;
                    size_t block_size = it->size;

                    // 移除空闲块
                    free_blocks_.erase(it);

                    // 如果块太大，分割它
                    if (block_size > aligned_size + alignment) {
                        FreeBlock remaining;
                        remaining.ptr = static_cast<char*>(ptr) + aligned_size;
                        remaining.size = block_size - aligned_size;
                        free_blocks_.push_back(remaining);
                    }

                    // 记录分配
                    allocated_blocks_[ptr] = aligned_size;
                    allocated_size_ += aligned_size;
                    stats_.current_usage += aligned_size;
                    stats_.peak_usage = std::max(stats_.peak_usage, stats_.current_usage);
                    stats_.allocation_count++;

                    return ptr;
                }
            }

            // 没有合适的空闲块，分配失败
            return nullptr;
        }

        void deallocate(void* ptr, size_t size) {
            if (!ptr) {
                return;
            }

            std::lock_guard<std::mutex> lock(mutex_);

            auto it = allocated_blocks_.find(ptr);
            if (it != allocated_blocks_.end()) {
                size_t block_size = it->second;
                allocated_blocks_.erase(it);

                // 添加到空闲块列表
                FreeBlock free_block;
                free_block.ptr = ptr;
                free_block.size = block_size;
                free_blocks_.push_back(free_block);

                // 尝试合并相邻的空闲块
                merge_free_blocks();

                allocated_size_ -= block_size;
                stats_.current_usage -= block_size;
                stats_.deallocation_count++;
            }
        }

        size_t get_allocated_size() const {
            std::lock_guard<std::mutex> lock(mutex_);
            return allocated_size_;
        }

        MemoryStats get_stats() const {
            std::lock_guard<std::mutex> lock(mutex_);
            MemoryStats current_stats = stats_;
            current_stats.fragmentation_ratio = calculate_fragmentation_ratio();
            return current_stats;
        }

        void compact() {
            std::lock_guard<std::mutex> lock(mutex_);
            merge_free_blocks();
        }

        void reset() {
            std::lock_guard<std::mutex> lock(mutex_);
            allocated_blocks_.clear();
            free_blocks_.clear();
            allocated_size_ = 0;
            stats_ = MemoryStats{};
            initialize_pool();
        }

    private:
        struct FreeBlock {
            void* ptr;
            size_t size;
        };

        void initialize_pool() {
            // 分配大内存池
            #ifdef HUSHELL_PLATFORM_WINDOWS
            pool_memory_ = VirtualAlloc(nullptr, pool_size_, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);
            #else
            pool_memory_ = mmap(nullptr, pool_size_, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
            if (pool_memory_ == MAP_FAILED) {
                pool_memory_ = nullptr;
            }
            #endif

            if (pool_memory_) {
                FreeBlock initial_block;
                initial_block.ptr = pool_memory_;
                initial_block.size = pool_size_;
                free_blocks_.push_back(initial_block);
            }
        }

        void cleanup_pool() {
            if (pool_memory_) {
                #ifdef HUSHELL_PLATFORM_WINDOWS
                VirtualFree(pool_memory_, 0, MEM_RELEASE);
                #else
                munmap(pool_memory_, pool_size_);
                #endif
            }
        }

        void merge_free_blocks() {
            // 按地址排序空闲块
            std::sort(free_blocks_.begin(), free_blocks_.end(), 
                [](const FreeBlock& a, const FreeBlock& b) {
                    return a.ptr < b.ptr;
                });

            // 合并相邻的空闲块
            for (size_t i = 0; i < free_blocks_.size() - 1; ) {
                char* current_end = static_cast<char*>(free_blocks_[i].ptr) + free_blocks_[i].size;
                if (current_end == free_blocks_[i + 1].ptr) {
                    // 合并块
                    free_blocks_[i].size += free_blocks_[i + 1].size;
                    free_blocks_.erase(free_blocks_.begin() + i + 1);
                } else {
                    ++i;
                }
            }
        }

        double calculate_fragmentation_ratio() const {
            if (free_blocks_.empty()) {
                return 0.0;
            }

            size_t total_free = 0;
            size_t largest_free = 0;
            for (const auto& block : free_blocks_) {
                total_free += block.size;
                largest_free = std::max(largest_free, block.size);
            }

            return total_free > 0 ? 1.0 - (static_cast<double>(largest_free) / total_free) : 0.0;
        }

        mutable std::mutex mutex_;
        size_t pool_size_;
        void* pool_memory_ = nullptr;
        std::vector<FreeBlock> free_blocks_;
        std::unordered_map<void*, size_t> allocated_blocks_;
        std::atomic<size_t> allocated_size_;
        MemoryStats stats_;
    };

    HighPerformanceAllocator::HighPerformanceAllocator(size_t pool_size) 
        : pimpl_(std::make_unique<Impl>(pool_size)) {}

    HighPerformanceAllocator::~HighPerformanceAllocator() = default;

    void* HighPerformanceAllocator::allocate(size_t size, size_t alignment) {
        return pimpl_->allocate(size, alignment);
    }

    void HighPerformanceAllocator::deallocate(void* ptr, size_t size) {
        pimpl_->deallocate(ptr, size);
    }

    size_t HighPerformanceAllocator::get_allocated_size() const {
        return pimpl_->get_allocated_size();
    }

    MemoryStats HighPerformanceAllocator::get_stats() const {
        return pimpl_->get_stats();
    }

    void HighPerformanceAllocator::compact() {
        pimpl_->compact();
    }

    void HighPerformanceAllocator::reset() {
        pimpl_->reset();
    }

    // ==================== MemoryManager 实现 ====================

    MemoryManager& MemoryManager::instance() {
        static MemoryManager instance;
        return instance;
    }

    Result<void> MemoryManager::initialize(const std::unordered_map<std::string, std::string>& config) {
        if (initialized_.load()) {
            return Result<void>::success();
        }

        std::lock_guard<std::mutex> lock(config_mutex_);
        
        try {
            // 更新配置
            config_ = config;

            // 初始化GPU内存池
            gpu_pool_ = std::make_unique<GPUMemoryPool>();

            // 初始化内存映射器
            memory_mapper_ = std::make_unique<MemoryMapper>();

            // 初始化高性能分配器
            size_t pool_size = 64 * 1024 * 1024; // 默认64MB
            auto it = config.find("allocator_pool_size_mb");
            if (it != config.end()) {
                pool_size = std::stoull(it->second) * 1024 * 1024;
            }
            allocator_ = std::make_unique<HighPerformanceAllocator>(pool_size);

            initialized_.store(true);
            return Result<void>::success();
        } catch (const std::exception& e) {
            return Result<void>::error(ErrorCode::INTERNAL_ERROR, e.what());
        }
    }

    void MemoryManager::shutdown() {
        if (!initialized_.load()) {
            return;
        }

        std::lock_guard<std::mutex> lock(config_mutex_);
        
        // 清理资源
        allocator_.reset();
        memory_mapper_.reset();
        gpu_pool_.reset();
        object_pools_.clear();

        initialized_.store(false);
    }

    GPUMemoryPool& MemoryManager::get_gpu_memory_pool() {
        if (!gpu_pool_) {
            throw std::runtime_error("GPU memory pool not initialized");
        }
        return *gpu_pool_;
    }

    MemoryMapper& MemoryManager::get_memory_mapper() {
        if (!memory_mapper_) {
            throw std::runtime_error("Memory mapper not initialized");
        }
        return *memory_mapper_;
    }

    HighPerformanceAllocator& MemoryManager::get_allocator() {
        if (!allocator_) {
            throw std::runtime_error("High performance allocator not initialized");
        }
        return *allocator_;
    }

    MemoryStats MemoryManager::get_global_stats() const {
        MemoryStats global_stats;
        
        if (allocator_) {
            auto alloc_stats = allocator_->get_stats();
            global_stats.current_usage += alloc_stats.current_usage;
            global_stats.peak_usage += alloc_stats.peak_usage;
            global_stats.allocation_count += alloc_stats.allocation_count;
            global_stats.deallocation_count += alloc_stats.deallocation_count;
        }

        if (gpu_pool_) {
            auto gpu_stats = gpu_pool_->get_gpu_stats();
            global_stats.gpu_current_usage = gpu_stats.gpu_current_usage;
            global_stats.gpu_peak_usage = gpu_stats.gpu_peak_usage;
            global_stats.gpu_total_allocated = gpu_stats.gpu_total_allocated;
        }

        return global_stats;
    }

    std::string MemoryManager::generate_memory_report() const {
        auto stats = get_global_stats();
        
        std::ostringstream report;
        report << "=== Memory Manager Report ===\n";
        report << "Current Usage: " << stats.current_usage / 1024 / 1024 << " MB\n";
        report << "Peak Usage: " << stats.peak_usage / 1024 / 1024 << " MB\n";
        report << "Allocations: " << stats.allocation_count << "\n";
        report << "Deallocations: " << stats.deallocation_count << "\n";
        report << "Fragmentation: " << (stats.fragmentation_ratio * 100) << "%\n";
        
        if (stats.gpu_current_usage > 0) {
            report << "GPU Current Usage: " << stats.gpu_current_usage / 1024 / 1024 << " MB\n";
            report << "GPU Peak Usage: " << stats.gpu_peak_usage / 1024 / 1024 << " MB\n";
        }

        return report.str();
    }

    bool MemoryManager::is_memory_healthy() const {
        auto stats = get_global_stats();
        
        // 检查碎片化程度
        if (stats.fragmentation_ratio > 0.5) {
            return false;
        }

        // 检查内存使用率（假设我们有最大限制）
        // 这里可以根据实际需求添加更多健康检查逻辑

        return true;
    }

    void MemoryManager::force_gc() {
        // 强制垃圾回收 - 压缩内存池
        if (allocator_) {
            allocator_->compact();
        }

        // 清理GPU内存池
        if (gpu_pool_) {
            gpu_pool_->cleanup();
        }
    }

    void MemoryManager::compact_memory() {
        if (allocator_) {
            allocator_->compact();
        }
    }

    void MemoryManager::update_config(const std::unordered_map<std::string, std::string>& config) {
        std::lock_guard<std::mutex> lock(config_mutex_);
        config_ = config;
    }

    std::unordered_map<std::string, std::string> MemoryManager::get_config() const {
        std::lock_guard<std::mutex> lock(config_mutex_);
        return config_;
    }

} // namespace hushell::core::memory