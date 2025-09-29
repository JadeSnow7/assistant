#pragma once

#include "async_types.hpp"
#include "../platform_config.h"
#include <memory>
#include <vector>
#include <unordered_map>
#include <mutex>
#include <atomic>
#include <cstddef>
#include <type_traits>

namespace hushell::core::memory {

    /**
     * @brief 内存统计信息
     */
    struct MemoryStats {
        size_t total_allocated = 0;
        size_t total_deallocated = 0;
        size_t current_usage = 0;
        size_t peak_usage = 0;
        size_t allocation_count = 0;
        size_t deallocation_count = 0;
        double fragmentation_ratio = 0.0;
        
        // GPU内存统计（如果支持）
        size_t gpu_total_allocated = 0;
        size_t gpu_current_usage = 0;
        size_t gpu_peak_usage = 0;
    };

    /**
     * @brief 内存块信息
     */
    struct MemoryBlock {
        void* ptr = nullptr;
        size_t size = 0;
        size_t alignment = 0;
        bool is_gpu_memory = false;
        std::chrono::steady_clock::time_point allocated_at;
    };

    /**
     * @brief 智能对象池 - 高性能对象复用
     */
    template<typename T>
    class ObjectPool {
    public:
        /**
         * @brief 构造函数
         * @param initial_size 初始池大小
         * @param max_size 最大池大小
         */
        explicit ObjectPool(size_t initial_size = 10, size_t max_size = 1000)
            : max_size_(max_size) {
            pool_.reserve(initial_size);
            for (size_t i = 0; i < initial_size; ++i) {
                pool_.emplace_back(std::make_unique<T>());
            }
        }

        /**
         * @brief 析构函数
         */
        ~ObjectPool() = default;

        /**
         * @brief 获取对象
         */
        std::unique_ptr<T> acquire() {
            std::lock_guard<std::mutex> lock(mutex_);
            
            if (!pool_.empty()) {
                auto obj = std::move(pool_.back());
                pool_.pop_back();
                ++acquired_count_;
                return obj;
            }
            
            // 池为空，创建新对象
            ++allocated_count_;
            return std::make_unique<T>();
        }

        /**
         * @brief 归还对象
         */
        void release(std::unique_ptr<T> obj) {
            if (!obj) {
                return;
            }

            std::lock_guard<std::mutex> lock(mutex_);
            
            if (pool_.size() < max_size_) {
                // 重置对象状态（如果需要）
                if constexpr (requires { obj->reset(); }) {
                    obj->reset();
                }
                pool_.emplace_back(std::move(obj));
                ++released_count_;
            }
            // 如果池已满，对象将被自动销毁
        }

        /**
         * @brief 获取池容量
         */
        size_t capacity() const {
            std::lock_guard<std::mutex> lock(mutex_);
            return max_size_;
        }

        /**
         * @brief 获取可用对象数量
         */
        size_t available() const {
            std::lock_guard<std::mutex> lock(mutex_);
            return pool_.size();
        }

        /**
         * @brief 获取统计信息
         */
        struct PoolStats {
            size_t allocated_count = 0;
            size_t acquired_count = 0;
            size_t released_count = 0;
            size_t available_count = 0;
            size_t capacity = 0;
        };

        PoolStats get_stats() const {
            std::lock_guard<std::mutex> lock(mutex_);
            return {
                allocated_count_.load(),
                acquired_count_.load(),
                released_count_.load(),
                pool_.size(),
                max_size_
            };
        }

    private:
        mutable std::mutex mutex_;
        std::vector<std::unique_ptr<T>> pool_;
        size_t max_size_;
        std::atomic<size_t> allocated_count_{0};
        std::atomic<size_t> acquired_count_{0};
        std::atomic<size_t> released_count_{0};
    };

    /**
     * @brief GPU内存池 - CUDA/OpenCL内存管理
     */
    class GPUMemoryPool {
    public:
        GPUMemoryPool();
        ~GPUMemoryPool();

        /**
         * @brief 分配GPU内存
         */
        void* allocate_gpu(size_t size, size_t alignment = 256);

        /**
         * @brief 释放GPU内存
         */
        void deallocate_gpu(void* ptr);

        /**
         * @brief 获取GPU内存统计
         */
        MemoryStats get_gpu_stats() const;

        /**
         * @brief 检查GPU内存可用性
         */
        bool is_gpu_memory_available() const;

        /**
         * @brief 清理GPU内存池
         */
        void cleanup();

    private:
        class Impl;
        std::unique_ptr<Impl> pimpl_;
    };

    /**
     * @brief 跨平台内存映射器
     */
    class MemoryMapper {
    public:
        MemoryMapper() = default;
        ~MemoryMapper();

        /**
         * @brief 映射文件到内存
         */
        void* map_file(const std::filesystem::path& path, size_t size = 0, bool read_only = true);

        /**
         * @brief 取消文件映射
         */
        void unmap_file(void* addr, size_t size);

        /**
         * @brief 创建匿名内存映射
         */
        void* map_anonymous(size_t size, bool executable = false);

        /**
         * @brief 获取页面大小
         */
        static size_t get_page_size();

        /**
         * @brief 获取大页面大小（如果支持）
         */
        static size_t get_large_page_size();

    private:
        std::unordered_map<void*, size_t> mapped_regions_;
        mutable std::mutex mutex_;
    };

    /**
     * @brief 高性能内存分配器
     */
    class HighPerformanceAllocator {
    public:
        /**
         * @brief 构造函数
         */
        explicit HighPerformanceAllocator(size_t pool_size = 64 * 1024 * 1024);  // 64MB默认

        /**
         * @brief 析构函数
         */
        ~HighPerformanceAllocator();

        /**
         * @brief 分配内存
         */
        void* allocate(size_t size, size_t alignment = sizeof(void*));

        /**
         * @brief 释放内存
         */
        void deallocate(void* ptr, size_t size);

        /**
         * @brief 获取已分配大小
         */
        size_t get_allocated_size() const;

        /**
         * @brief 获取内存统计
         */
        MemoryStats get_stats() const;

        /**
         * @brief 压缩内存池（减少碎片）
         */
        void compact();

        /**
         * @brief 重置分配器
         */
        void reset();

    private:
        class Impl;
        std::unique_ptr<Impl> pimpl_;
    };

    /**
     * @brief 内存管理器 - 统一内存管理接口
     */
    class MemoryManager {
    public:
        /**
         * @brief 获取单例实例
         */
        static MemoryManager& instance();

        /**
         * @brief 初始化内存管理器
         */
        Result<void> initialize(const std::unordered_map<std::string, std::string>& config = {});

        /**
         * @brief 关闭内存管理器
         */
        void shutdown();

        // ========== 对象池管理 ==========

        /**
         * @brief 获取或创建对象池
         */
        template<typename T>
        ObjectPool<T>& get_object_pool() {
            std::lock_guard<std::mutex> lock(pools_mutex_);
            
            auto type_name = typeid(T).name();
            auto it = object_pools_.find(type_name);
            
            if (it == object_pools_.end()) {
                auto pool = std::make_unique<ObjectPool<T>>();
                auto* pool_ptr = pool.get();
                object_pools_[type_name] = std::move(pool);
                return *pool_ptr;
            }
            
            return *static_cast<ObjectPool<T>*>(it->second.get());
        }

        // ========== GPU内存管理 ==========

        /**
         * @brief 获取GPU内存池
         */
        GPUMemoryPool& get_gpu_memory_pool();

        // ========== 内存映射 ==========

        /**
         * @brief 获取内存映射器
         */
        MemoryMapper& get_memory_mapper();

        // ========== 高性能分配器 ==========

        /**
         * @brief 获取高性能分配器
         */
        HighPerformanceAllocator& get_allocator();

        // ========== 统计和监控 ==========

        /**
         * @brief 获取全局内存统计
         */
        MemoryStats get_global_stats() const;

        /**
         * @brief 获取内存使用报告
         */
        std::string generate_memory_report() const;

        /**
         * @brief 检查内存健康状态
         */
        bool is_memory_healthy() const;

        /**
         * @brief 强制垃圾回收
         */
        void force_gc();

        /**
         * @brief 内存压缩
         */
        void compact_memory();

        // ========== 配置管理 ==========

        /**
         * @brief 更新配置
         */
        void update_config(const std::unordered_map<std::string, std::string>& config);

        /**
         * @brief 获取配置
         */
        std::unordered_map<std::string, std::string> get_config() const;

    private:
        MemoryManager() = default;
        ~MemoryManager() = default;

        // 禁用拷贝和移动
        MemoryManager(const MemoryManager&) = delete;
        MemoryManager& operator=(const MemoryManager&) = delete;

        mutable std::mutex pools_mutex_;
        std::unordered_map<std::string, std::unique_ptr<void, std::function<void(void*)>>> object_pools_;
        
        std::unique_ptr<GPUMemoryPool> gpu_pool_;
        std::unique_ptr<MemoryMapper> memory_mapper_;
        std::unique_ptr<HighPerformanceAllocator> allocator_;
        
        std::atomic<bool> initialized_{false};
        mutable std::mutex config_mutex_;
        std::unordered_map<std::string, std::string> config_;
    };

    /**
     * @brief RAII智能内存块包装器
     */
    template<typename T>
    class ManagedMemoryBlock {
    public:
        ManagedMemoryBlock(size_t count = 1) 
            : size_(count * sizeof(T)) {
            auto& allocator = MemoryManager::instance().get_allocator();
            ptr_ = static_cast<T*>(allocator.allocate(size_, alignof(T)));
            
            if (!ptr_) {
                throw std::bad_alloc();
            }
        }

        ~ManagedMemoryBlock() {
            if (ptr_) {
                auto& allocator = MemoryManager::instance().get_allocator();
                allocator.deallocate(ptr_, size_);
            }
        }

        // 禁用拷贝
        ManagedMemoryBlock(const ManagedMemoryBlock&) = delete;
        ManagedMemoryBlock& operator=(const ManagedMemoryBlock&) = delete;

        // 移动构造和赋值
        ManagedMemoryBlock(ManagedMemoryBlock&& other) noexcept
            : ptr_(std::exchange(other.ptr_, nullptr)), size_(std::exchange(other.size_, 0)) {}

        ManagedMemoryBlock& operator=(ManagedMemoryBlock&& other) noexcept {
            if (this != &other) {
                if (ptr_) {
                    auto& allocator = MemoryManager::instance().get_allocator();
                    allocator.deallocate(ptr_, size_);
                }
                ptr_ = std::exchange(other.ptr_, nullptr);
                size_ = std::exchange(other.size_, 0);
            }
            return *this;
        }

        T* get() const noexcept { return ptr_; }
        T& operator*() const { return *ptr_; }
        T* operator->() const { return ptr_; }
        T& operator[](size_t index) const { return ptr_[index]; }

        explicit operator bool() const noexcept { return ptr_ != nullptr; }
        size_t size() const noexcept { return size_; }

    private:
        T* ptr_ = nullptr;
        size_t size_ = 0;
    };

} // namespace hushell::core::memory