#include "../include/memory_optimizer.hpp"
#include <algorithm>
#include <thread>
#include <condition_variable>
#include <queue>

namespace ai_assistant {

// HighPerformanceMemoryPool实现
class HighPerformanceMemoryPool::Impl {
public:
    Impl(size_t pool_size_mb, size_t alignment) 
        : pool_size_bytes_(pool_size_mb * 1024 * 1024)
        , alignment_(alignment)
        , fragmentation_threshold_(0.3)
        , auto_management_enabled_(false) {
        
        // 分配大块内存
        pool_base_ = aligned_alloc<64>(pool_size_bytes_);
        if (!pool_base_) {
            Logger::error("Failed to allocate memory pool");
            return;
        }
        
        // 初始化为一个大的空闲块
        MemoryBlock initial_block;
        initial_block.ptr = pool_base_;
        initial_block.size = pool_size_bytes_;
        initial_block.alignment = alignment_;
        initial_block.in_use = false;
        initial_block.last_used = std::chrono::steady_clock::now();
        initial_block.reference_count = 0;
        
        free_blocks_.push_back(initial_block);
        Logger::info("Memory pool initialized: " + std::to_string(pool_size_mb) + "MB");
    }
    
    ~Impl() {
        if (pool_base_) {
            aligned_free(pool_base_);
        }
    }
    
    void* allocate(size_t size) {
        return allocate_aligned(size, alignment_);
    }
    
    void* allocate_aligned(size_t size, size_t alignment) {
        std::lock_guard<std::shared_mutex> lock(mutex_);
        
        // 对齐大小
        size = align_size(size, alignment);
        
        // 查找合适的空闲块
        for (auto it = free_blocks_.begin(); it != free_blocks_.end(); ++it) {
            if (!it->in_use && it->size >= size) {
                void* aligned_ptr = align_pointer(it->ptr, alignment);
                size_t offset = static_cast<char*>(aligned_ptr) - static_cast<char*>(it->ptr);
                
                if (it->size >= size + offset) {
                    // 标记为已使用
                    it->in_use = true;
                    it->last_used = std::chrono::steady_clock::now();
                    it->reference_count = 1;
                    
                    // 如果有前置偏移，创建新的空闲块
                    if (offset > 0) {
                        MemoryBlock prefix_block;
                        prefix_block.ptr = it->ptr;
                        prefix_block.size = offset;
                        prefix_block.alignment = alignment_;
                        prefix_block.in_use = false;
                        prefix_block.last_used = std::chrono::steady_clock::now();
                        prefix_block.reference_count = 0;
                        
                        free_blocks_.insert(it, prefix_block);
                    }
                    
                    // 如果块太大，分割剩余部分
                    if (it->size > size + offset + alignment) {
                        MemoryBlock remaining_block;
                        remaining_block.ptr = static_cast<char*>(aligned_ptr) + size;
                        remaining_block.size = it->size - size - offset;
                        remaining_block.alignment = alignment_;
                        remaining_block.in_use = false;
                        remaining_block.last_used = std::chrono::steady_clock::now();
                        remaining_block.reference_count = 0;
                        
                        free_blocks_.insert(it + 1, remaining_block);
                    }
                    
                    // 更新当前块信息
                    it->ptr = aligned_ptr;
                    it->size = size;
                    it->alignment = alignment;
                    
                    // 移动到已使用列表
                    used_blocks_.push_back(*it);
                    free_blocks_.erase(it);
                    
                    // 更新统计
                    total_allocated_ += size;
                    peak_usage_ = std::max(peak_usage_, total_allocated_);
                    allocation_count_++;
                    
                    return aligned_ptr;
                }
            }
        }
        
        Logger::warning("Memory pool allocation failed for size: " + std::to_string(size));
        return nullptr;
    }
    
    void deallocate(void* ptr) {
        if (!ptr) return;
        
        std::lock_guard<std::shared_mutex> lock(mutex_);
        
        // 在已使用块中查找
        for (auto it = used_blocks_.begin(); it != used_blocks_.end(); ++it) {
            if (it->ptr == ptr) {
                // 更新统计
                total_allocated_ -= it->size;
                deallocation_count_++;
                
                // 移回空闲列表
                it->in_use = false;
                it->last_used = std::chrono::steady_clock::now();
                it->reference_count = 0;
                
                free_blocks_.push_back(*it);
                used_blocks_.erase(it);
                
                // 尝试合并相邻块
                merge_adjacent_blocks();
                
                return;
            }
        }
        
        Logger::warning("Attempt to deallocate unknown pointer");
    }
    
    MemoryStats get_memory_stats() const {
        std::shared_lock<std::shared_mutex> lock(mutex_);
        
        MemoryStats stats;
        stats.total_size_mb = pool_size_bytes_ / (1024 * 1024);
        stats.used_size_mb = total_allocated_ / (1024 * 1024);
        stats.free_size_mb = (pool_size_bytes_ - total_allocated_) / (1024 * 1024);
        stats.peak_usage_mb = peak_usage_ / (1024 * 1024);
        stats.allocation_count = allocation_count_;
        stats.deallocation_count = deallocation_count_;
        
        // 计算最大空闲块
        size_t largest_free = 0;
        for (const auto& block : free_blocks_) {
            if (!block.in_use && block.size > largest_free) {
                largest_free = block.size;
            }
        }
        stats.largest_free_block_mb = largest_free / (1024 * 1024);
        
        // 计算碎片化率
        stats.fragmentation_ratio = calculate_fragmentation_ratio();
        
        return stats;
    }
    
    void defragment() {
        std::lock_guard<std::shared_mutex> lock(mutex_);
        merge_adjacent_blocks();
        compact_memory_layout();
    }

private:
    void* pool_base_;
    size_t pool_size_bytes_;
    size_t alignment_;
    double fragmentation_threshold_;
    bool auto_management_enabled_;
    
    std::vector<MemoryBlock> free_blocks_;
    std::vector<MemoryBlock> used_blocks_;
    
    mutable std::shared_mutex mutex_;
    
    size_t total_allocated_ = 0;
    size_t peak_usage_ = 0;
    size_t allocation_count_ = 0;
    size_t deallocation_count_ = 0;
    
    size_t align_size(size_t size, size_t alignment) const {
        return ((size + alignment - 1) / alignment) * alignment;
    }
    
    void* align_pointer(void* ptr, size_t alignment) const {
        uintptr_t addr = reinterpret_cast<uintptr_t>(ptr);
        uintptr_t aligned_addr = ((addr + alignment - 1) / alignment) * alignment;
        return reinterpret_cast<void*>(aligned_addr);
    }
    
    void merge_adjacent_blocks() {
        // 按地址排序空闲块
        std::sort(free_blocks_.begin(), free_blocks_.end(),
                 [](const MemoryBlock& a, const MemoryBlock& b) {
                     return a.ptr < b.ptr;
                 });
        
        // 合并相邻空闲块
        for (size_t i = 0; i < free_blocks_.size(); ) {
            if (i + 1 < free_blocks_.size()) {
                char* current_end = static_cast<char*>(free_blocks_[i].ptr) + free_blocks_[i].size;
                char* next_start = static_cast<char*>(free_blocks_[i + 1].ptr);
                
                if (current_end == next_start && !free_blocks_[i].in_use && !free_blocks_[i + 1].in_use) {
                    // 合并块
                    free_blocks_[i].size += free_blocks_[i + 1].size;
                    free_blocks_.erase(free_blocks_.begin() + i + 1);
                    continue; // 不增加i，继续检查下一个块
                }
            }
            ++i;
        }
    }
    
    void compact_memory_layout() {
        // 这里可以实现更复杂的内存紧缩算法
        // 由于涉及移动已分配的内存，需要更新指针引用
        // 简化实现中暂时跳过
    }
    
    double calculate_fragmentation_ratio() const {
        if (free_blocks_.empty()) return 0.0;
        
        size_t free_block_count = 0;
        size_t total_free_size = 0;
        
        for (const auto& block : free_blocks_) {
            if (!block.in_use) {
                free_block_count++;
                total_free_size += block.size;
            }
        }
        
        if (free_block_count <= 1 || total_free_size == 0) return 0.0;
        
        // 碎片化率 = (空闲块数量 - 1) / 总空闲空间
        return static_cast<double>(free_block_count - 1) / free_block_count;
    }
};

// SessionManager实现
class SessionManager::Impl {
public:
    Impl(size_t max_sessions, std::chrono::minutes timeout)
        : max_sessions_(max_sessions)
        , session_timeout_(timeout)
        , memory_limit_mb_(1024)
        , total_memory_usage_(0) {}
    
    bool create_session(const std::string& session_id, std::shared_ptr<void> context_data, size_t memory_usage) {
        std::lock_guard<std::shared_mutex> lock(mutex_);
        
        // 检查会话是否已存在
        if (sessions_.find(session_id) != sessions_.end()) {
            return false;
        }
        
        // 检查内存限制
        if (total_memory_usage_ + memory_usage > memory_limit_mb_ * 1024 * 1024) {
            // 尝试清理过期会话
            cleanup_expired_sessions_internal();
            
            if (total_memory_usage_ + memory_usage > memory_limit_mb_ * 1024 * 1024) {
                // 强制驱逐最老的会话
                evict_oldest_sessions_internal(1);
            }
        }
        
        // 检查会话数限制
        if (sessions_.size() >= max_sessions_) {
            evict_oldest_sessions_internal(1);
        }
        
        // 创建新会话
        SessionData session;
        session.session_id = session_id;
        session.context_data = context_data;
        session.memory_usage = memory_usage;
        session.created_time = std::chrono::steady_clock::now();
        session.last_access = session.created_time;
        session.access_count = 1;
        session.is_active = true;
        
        sessions_[session_id] = std::make_shared<SessionData>(session);
        total_memory_usage_ += memory_usage;
        
        return true;
    }
    
    std::shared_ptr<SessionData> get_session(const std::string& session_id) {
        std::shared_lock<std::shared_mutex> lock(mutex_);
        
        auto it = sessions_.find(session_id);
        if (it != sessions_.end()) {
            // 更新访问时间
            it->second->last_access = std::chrono::steady_clock::now();
            it->second->access_count++;
            return it->second;
        }
        
        return nullptr;
    }
    
    size_t cleanup_expired_sessions() {
        std::lock_guard<std::shared_mutex> lock(mutex_);
        return cleanup_expired_sessions_internal();
    }
    
    SessionStats get_session_stats() const {
        std::shared_lock<std::shared_mutex> lock(mutex_);
        
        SessionStats stats;
        stats.total_sessions = sessions_.size();
        stats.active_sessions = 0;
        stats.expired_sessions = 0;
        stats.total_memory_usage_mb = total_memory_usage_ / (1024 * 1024);
        
        auto now = std::chrono::steady_clock::now();
        std::chrono::minutes total_age{0};
        
        for (const auto& [id, session] : sessions_) {
            auto age = std::chrono::duration_cast<std::chrono::minutes>(now - session->created_time);
            total_age += age;
            
            if (age > session_timeout_) {
                stats.expired_sessions++;
            } else {
                stats.active_sessions++;
            }
        }
        
        stats.avg_session_age = stats.total_sessions > 0 ? 
            total_age / stats.total_sessions : std::chrono::minutes(0);
        
        stats.memory_efficiency_ratio = memory_limit_mb_ > 0 ? 
            static_cast<double>(stats.total_memory_usage_mb) / memory_limit_mb_ : 0.0;
        
        return stats;
    }

private:
    std::unordered_map<std::string, std::shared_ptr<SessionData>> sessions_;
    mutable std::shared_mutex mutex_;
    
    size_t max_sessions_;
    std::chrono::minutes session_timeout_;
    size_t memory_limit_mb_;
    size_t total_memory_usage_;
    
    size_t cleanup_expired_sessions_internal() {
        auto now = std::chrono::steady_clock::now();
        size_t cleaned_count = 0;
        
        for (auto it = sessions_.begin(); it != sessions_.end();) {
            auto age = std::chrono::duration_cast<std::chrono::minutes>(now - it->second->last_access);
            
            if (age > session_timeout_) {
                total_memory_usage_ -= it->second->memory_usage;
                it = sessions_.erase(it);
                cleaned_count++;
            } else {
                ++it;
            }
        }
        
        return cleaned_count;
    }
    
    bool evict_oldest_sessions_internal(size_t count) {
        if (sessions_.empty()) return false;
        
        // 创建按访问时间排序的会话列表
        std::vector<std::pair<std::chrono::steady_clock::time_point, std::string>> session_times;
        
        for (const auto& [id, session] : sessions_) {
            session_times.emplace_back(session->last_access, id);
        }
        
        // 按访问时间排序（最老的在前）
        std::sort(session_times.begin(), session_times.end());
        
        // 驱逐最老的会话
        size_t evicted = 0;
        for (const auto& [time, id] : session_times) {
            if (evicted >= count) break;
            
            auto it = sessions_.find(id);
            if (it != sessions_.end()) {
                total_memory_usage_ -= it->second->memory_usage;
                sessions_.erase(it);
                evicted++;
            }
        }
        
        return evicted > 0;
    }
};

// 公共接口实现
HighPerformanceMemoryPool::HighPerformanceMemoryPool(size_t pool_size_mb, size_t alignment) 
    : pimpl_(std::make_unique<Impl>(pool_size_mb, alignment)) {}

HighPerformanceMemoryPool::~HighPerformanceMemoryPool() = default;

void* HighPerformanceMemoryPool::allocate(size_t size) {
    return pimpl_->allocate(size);
}

void* HighPerformanceMemoryPool::allocate_aligned(size_t size, size_t alignment) {
    return pimpl_->allocate_aligned(size, alignment);
}

void HighPerformanceMemoryPool::deallocate(void* ptr) {
    pimpl_->deallocate(ptr);
}

HighPerformanceMemoryPool::MemoryStats HighPerformanceMemoryPool::get_memory_stats() const {
    return pimpl_->get_memory_stats();
}

void HighPerformanceMemoryPool::defragment() {
    pimpl_->defragment();
}

SessionManager::SessionManager(size_t max_sessions, std::chrono::minutes session_timeout)
    : pimpl_(std::make_unique<Impl>(max_sessions, session_timeout)) {}

SessionManager::~SessionManager() = default;

bool SessionManager::create_session(const std::string& session_id, std::shared_ptr<void> context_data, size_t memory_usage) {
    return pimpl_->create_session(session_id, context_data, memory_usage);
}

std::shared_ptr<SessionManager::SessionData> SessionManager::get_session(const std::string& session_id) {
    return pimpl_->get_session(session_id);
}

size_t SessionManager::cleanup_expired_sessions() {
    return pimpl_->cleanup_expired_sessions();
}

SessionManager::SessionStats SessionManager::get_session_stats() const {
    return pimpl_->get_session_stats();
}

} // namespace ai_assistant