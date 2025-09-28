#pragma once

#include "common.hpp"
#include <memory>
#include <vector>
#include <atomic>
#include <mutex>
#include <shared_mutex>
#include <unordered_map>
#include <chrono>

namespace ai_assistant {

// 内存对齐工具
constexpr size_t CACHE_LINE_SIZE = 64;
constexpr size_t DEFAULT_ALIGNMENT = 32;

template<size_t Alignment = DEFAULT_ALIGNMENT>
inline void* aligned_alloc(size_t size) {
    return std::aligned_alloc(Alignment, (size + Alignment - 1) & ~(Alignment - 1));
}

inline void aligned_free(void* ptr) {
    std::free(ptr);
}

// 内存块信息
struct MemoryBlock {
    void* ptr;
    size_t size;
    size_t alignment;
    bool in_use;
    std::chrono::steady_clock::time_point last_used;
    size_t reference_count;
};

// 高性能内存池
template<typename T>
class LockFreeObjectPool {
public:
    LockFreeObjectPool(size_t initial_capacity = 1000);
    ~LockFreeObjectPool();
    
    // 获取对象
    T* acquire();
    
    // 释放对象
    void release(T* obj);
    
    // 获取统计信息
    struct Stats {
        size_t total_objects;
        size_t available_objects;
        size_t peak_usage;
        size_t allocation_count;
        size_t deallocation_count;
    };
    Stats get_stats() const;
    
    // 预分配对象
    void preallocate(size_t count);
    
    // 清理未使用的对象
    void cleanup();

private:
    struct alignas(CACHE_LINE_SIZE) Node {
        alignas(T) char data[sizeof(T)];
        std::atomic<Node*> next;
    };
    
    std::atomic<Node*> free_list_;
    std::vector<std::unique_ptr<Node[]>> chunks_;
    std::atomic<size_t> total_objects_;
    std::atomic<size_t> available_objects_;
    std::atomic<size_t> peak_usage_;
    std::atomic<size_t> allocation_count_;
    std::atomic<size_t> deallocation_count_;
    
    mutable std::shared_mutex mutex_;
    size_t chunk_size_;
    
    Node* allocate_new_chunk();
};

// 高性能内存池管理器
class HighPerformanceMemoryPool {
public:
    HighPerformanceMemoryPool(size_t pool_size_mb = 512, size_t alignment = DEFAULT_ALIGNMENT);
    ~HighPerformanceMemoryPool();
    
    // 分配内存
    void* allocate(size_t size);
    
    // 分配对齐内存
    void* allocate_aligned(size_t size, size_t alignment);
    
    // 释放内存
    void deallocate(void* ptr);
    
    // 批量分配
    std::vector<void*> batch_allocate(const std::vector<size_t>& sizes);
    
    // 批量释放
    void batch_deallocate(const std::vector<void*>& ptrs);
    
    // 内存整理
    void defragment();
    
    // 获取内存统计
    struct MemoryStats {
        size_t total_size_mb;
        size_t used_size_mb;
        size_t free_size_mb;
        size_t largest_free_block_mb;
        double fragmentation_ratio;
        size_t allocation_count;
        size_t deallocation_count;
        size_t peak_usage_mb;
    };
    MemoryStats get_memory_stats() const;
    
    // 设置内存压缩阈值
    void set_compaction_threshold(double fragmentation_threshold);
    
    // 自动内存管理
    void enable_auto_management(bool enable = true);
    
    // 预分配内存块
    bool preallocate_blocks(const std::vector<size_t>& block_sizes);
    
    // 内存使用率监控
    bool is_memory_pressure() const;
    
    // 清理未使用内存
    size_t cleanup_unused_memory(std::chrono::minutes age_threshold = std::chrono::minutes(5));

private:
    class Impl;
    std::unique_ptr<Impl> pimpl_;
};

// 智能会话管理器
class SessionManager {
public:
    struct SessionData {
        std::string session_id;
        std::shared_ptr<void> context_data;
        size_t memory_usage;
        std::chrono::steady_clock::time_point last_access;
        std::chrono::steady_clock::time_point created_time;
        size_t access_count;
        bool is_active;
    };
    
    SessionManager(size_t max_sessions = 1000, std::chrono::minutes session_timeout = std::chrono::minutes(30));
    ~SessionManager();
    
    // 创建会话
    bool create_session(const std::string& session_id, std::shared_ptr<void> context_data, size_t memory_usage);
    
    // 获取会话
    std::shared_ptr<SessionData> get_session(const std::string& session_id);
    
    // 更新会话访问
    void update_session_access(const std::string& session_id);
    
    // 删除会话
    bool remove_session(const std::string& session_id);
    
    // 清理过期会话
    size_t cleanup_expired_sessions();
    
    // 优化会话内存
    void optimize_session_memory();
    
    // 获取会话统计
    struct SessionStats {
        size_t total_sessions;
        size_t active_sessions;
        size_t expired_sessions;
        size_t total_memory_usage_mb;
        std::chrono::minutes avg_session_age;
        double memory_efficiency_ratio;
    };
    SessionStats get_session_stats() const;
    
    // 设置会话限制
    void set_memory_limit(size_t limit_mb);
    void set_session_limit(size_t max_sessions);
    void set_session_timeout(std::chrono::minutes timeout);
    
    // 获取所有活跃会话
    std::vector<std::string> get_active_sessions() const;
    
    // 强制清理最老的会话
    bool evict_oldest_sessions(size_t count);

private:
    class Impl;
    std::unique_ptr<Impl> pimpl_;
};

// 内存压缩器
class MemoryCompressor {
public:
    enum class CompressionAlgorithm {
        LZ4,
        ZSTD,
        SNAPPY
    };
    
    MemoryCompressor(CompressionAlgorithm algorithm = CompressionAlgorithm::LZ4);
    ~MemoryCompressor();
    
    // 压缩数据
    std::vector<uint8_t> compress(const void* data, size_t size);
    
    // 解压数据
    std::vector<uint8_t> decompress(const void* compressed_data, size_t compressed_size);
    
    // 批量压缩
    std::vector<std::vector<uint8_t>> batch_compress(const std::vector<std::pair<const void*, size_t>>& data_list);
    
    // 获取压缩统计
    struct CompressionStats {
        size_t total_compressed_count;
        size_t total_decompressed_count;
        size_t total_original_bytes;
        size_t total_compressed_bytes;
        double avg_compression_ratio;
        std::chrono::milliseconds avg_compression_time;
        std::chrono::milliseconds avg_decompression_time;
    };
    CompressionStats get_compression_stats() const;
    
    // 设置压缩级别
    void set_compression_level(int level);
    
    // 异步压缩
    std::future<std::vector<uint8_t>> compress_async(const void* data, size_t size);

private:
    class Impl;
    std::unique_ptr<Impl> pimpl_;
};

// 内存监控器  
class MemoryMonitor {
public:
    struct MemorySnapshot {
        std::chrono::steady_clock::time_point timestamp;
        size_t virtual_memory_mb;
        size_t physical_memory_mb;
        size_t heap_memory_mb;
        size_t pool_memory_mb;
        double fragmentation_ratio;
        size_t allocation_rate_per_sec;
        size_t deallocation_rate_per_sec;
    };
    
    MemoryMonitor();
    ~MemoryMonitor();
    
    // 开始监控
    bool start_monitoring(std::chrono::milliseconds interval = std::chrono::milliseconds(1000));
    
    // 停止监控
    void stop_monitoring();
    
    // 获取当前快照
    MemorySnapshot get_current_snapshot() const;
    
    // 获取历史快照
    std::vector<MemorySnapshot> get_historical_snapshots(size_t count = 100) const;
    
    // 检测内存泄漏
    bool detect_memory_leak(std::chrono::minutes window = std::chrono::minutes(10)) const;
    
    // 获取内存使用趋势
    enum class MemoryTrend {
        STABLE,
        INCREASING,
        DECREASING,
        FLUCTUATING
    };
    MemoryTrend analyze_memory_trend(std::chrono::minutes window = std::chrono::minutes(5)) const;
    
    // 设置内存告警阈值
    void set_alert_thresholds(size_t warning_mb, size_t critical_mb);
    
    // 注册内存事件回调
    using MemoryCallback = std::function<void(const MemorySnapshot&)>;
    void register_callback(const std::string& name, MemoryCallback callback);
    
    // 导出内存报告
    bool export_memory_report(const std::string& file_path) const;

private:
    class Impl;
    std::unique_ptr<Impl> pimpl_;
};

// RAII内存管理器
template<typename T>
class ScopedMemoryManager {
public:
    ScopedMemoryManager(HighPerformanceMemoryPool& pool, size_t count = 1)
        : pool_(pool), count_(count) {
        ptr_ = static_cast<T*>(pool_.allocate(sizeof(T) * count));
        if (ptr_) {
            for (size_t i = 0; i < count; ++i) {
                new (ptr_ + i) T();
            }
        }
    }
    
    ~ScopedMemoryManager() {
        if (ptr_) {
            for (size_t i = 0; i < count_; ++i) {
                (ptr_ + i)->~T();
            }
            pool_.deallocate(ptr_);
        }
    }
    
    T* get() const { return ptr_; }
    T& operator*() const { return *ptr_; }
    T* operator->() const { return ptr_; }
    T& operator[](size_t index) const { return ptr_[index]; }
    
    bool is_valid() const { return ptr_ != nullptr; }
    size_t size() const { return count_; }

private:
    HighPerformanceMemoryPool& pool_;
    T* ptr_;
    size_t count_;
    
    // 禁止拷贝
    ScopedMemoryManager(const ScopedMemoryManager&) = delete;
    ScopedMemoryManager& operator=(const ScopedMemoryManager&) = delete;
};

// 内存优化建议生成器
class MemoryOptimizationAdvisor {
public:
    struct OptimizationSuggestion {
        enum class Priority {
            LOW,
            MEDIUM,
            HIGH,
            CRITICAL
        };
        
        Priority priority;
        std::string category;
        std::string description;
        std::string recommendation;
        size_t potential_memory_saving_mb;
        double implementation_difficulty; // 0.0-1.0
    };
    
    // 分析内存使用并生成建议
    static std::vector<OptimizationSuggestion> analyze_and_suggest(
        const HighPerformanceMemoryPool::MemoryStats& pool_stats,
        const SessionManager::SessionStats& session_stats,
        const MemoryMonitor::MemorySnapshot& snapshot
    );
    
    // 生成内存优化报告
    static std::string generate_optimization_report(
        const std::vector<OptimizationSuggestion>& suggestions
    );
};

} // namespace ai_assistant