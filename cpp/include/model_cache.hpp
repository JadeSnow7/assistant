#pragma once

#include "common.hpp"
#include "memory_optimizer.hpp"
#include <unordered_map>
#include <shared_mutex>
#include <chrono>
#include <future>

namespace ai_assistant {

// 模型信息
struct ModelInfo {
    std::string model_id;
    std::string model_path;
    std::string model_type; // "local", "cloud", "quantized"
    size_t model_size_mb;
    size_t memory_requirement_mb;
    std::chrono::steady_clock::time_point load_time;
    std::chrono::steady_clock::time_point last_access;
    size_t access_count;
    bool is_loaded;
    bool is_preloaded;
    double load_priority; // 0.0-1.0
};

// 模型缓存统计
struct ModelCacheStats {
    size_t total_models;
    size_t loaded_models;
    size_t cache_hits;
    size_t cache_misses;
    double hit_ratio;
    size_t total_memory_usage_mb;
    size_t available_cache_space_mb;
    std::chrono::milliseconds avg_load_time;
    size_t eviction_count;
};

// LRU缓存策略
class LRUEvictionPolicy {
public:
    // 选择要驱逐的模型
    std::vector<std::string> select_eviction_candidates(
        const std::unordered_map<std::string, ModelInfo>& models,
        size_t required_space_mb
    ) const;
    
    // 更新访问顺序
    void update_access_order(const std::string& model_id);
    
    // 获取访问顺序
    std::vector<std::string> get_access_order() const;

private:
    mutable std::shared_mutex mutex_;
    std::list<std::string> access_order_;
    std::unordered_map<std::string, std::list<std::string>::iterator> position_map_;
};

// 智能缓存策略
class IntelligentEvictionPolicy {
public:
    struct ModelUsagePattern {
        double frequency_score;    // 使用频率得分
        double recency_score;      // 最近使用得分
        double size_penalty;       // 大小惩罚
        double load_time_penalty;  // 加载时间惩罚
        double priority_bonus;     // 优先级奖励
        double total_score;        // 综合得分
    };
    
    // 计算模型使用模式得分
    ModelUsagePattern calculate_usage_pattern(const ModelInfo& model) const;
    
    // 选择驱逐候选
    std::vector<std::string> select_eviction_candidates(
        const std::unordered_map<std::string, ModelInfo>& models,
        size_t required_space_mb
    ) const;
    
    // 预测模型使用概率
    double predict_usage_probability(const ModelInfo& model) const;
    
    // 更新使用统计
    void update_usage_statistics(const std::string& model_id);

private:
    mutable std::shared_mutex mutex_;
    std::unordered_map<std::string, std::vector<std::chrono::steady_clock::time_point>> access_history_;
    
    double calculate_frequency_score(const ModelInfo& model) const;
    double calculate_recency_score(const ModelInfo& model) const;
    double calculate_size_penalty(const ModelInfo& model) const;
    double calculate_load_time_penalty(const ModelInfo& model) const;
};

// 模型缓存管理器
class ModelCache {
public:
    ModelCache(size_t cache_size_mb = 4096, std::unique_ptr<LRUEvictionPolicy> policy = nullptr);
    ~ModelCache();
    
    // 加载模型到缓存
    std::future<bool> load_model_async(const std::string& model_id, const std::string& model_path);
    
    // 同步加载模型
    bool load_model_sync(const std::string& model_id, const std::string& model_path);
    
    // 获取模型（如果未缓存则加载）
    std::shared_ptr<void> get_or_load_model(const std::string& model_id, const std::string& model_path = "");
    
    // 检查模型是否已缓存
    bool is_model_cached(const std::string& model_id) const;
    
    // 预加载常用模型
    void preload_frequently_used_models();
    
    // 预加载指定模型列表
    std::vector<std::future<bool>> preload_models(const std::vector<std::string>& model_ids);
    
    // 卸载模型
    bool unload_model(const std::string& model_id);
    
    // 清空缓存
    void clear_cache();
    
    // 优化缓存大小
    void optimize_cache_size(size_t target_memory_mb);
    
    // 设置缓存大小
    void set_cache_size(size_t cache_size_mb);
    
    // 获取缓存统计
    ModelCacheStats get_cache_stats() const;
    
    // 获取所有缓存的模型信息
    std::vector<ModelInfo> get_cached_models() const;
    
    // 设置模型优先级
    void set_model_priority(const std::string& model_id, double priority);
    
    // 启用/禁用自动缓存管理
    void enable_auto_management(bool enable = true);
    
    // 获取推荐的缓存配置
    struct CacheRecommendation {
        size_t recommended_cache_size_mb;
        std::vector<std::string> models_to_preload;
        std::vector<std::string> models_to_evict;
        double expected_hit_ratio;
    };
    CacheRecommendation get_cache_recommendations() const;

private:
    class Impl;
    std::unique_ptr<Impl> pimpl_;
};

// 模型预加载器
class ModelPreloader {
public:
    ModelPreloader(ModelCache& cache);
    ~ModelPreloader();
    
    // 分析使用模式并预加载
    void analyze_and_preload();
    
    // 添加预加载候选
    void add_preload_candidate(const std::string& model_id, double priority = 1.0);
    
    // 移除预加载候选
    void remove_preload_candidate(const std::string& model_id);
    
    // 设置预加载策略
    enum class PreloadStrategy {
        AGGRESSIVE,  // 积极预加载
        MODERATE,    // 适度预加载
        CONSERVATIVE // 保守预加载
    };
    void set_preload_strategy(PreloadStrategy strategy);
    
    // 启动预加载服务
    void start_preload_service(std::chrono::minutes check_interval = std::chrono::minutes(5));
    
    // 停止预加载服务
    void stop_preload_service();
    
    // 获取预加载统计
    struct PreloadStats {
        size_t preload_requests;
        size_t successful_preloads;
        size_t failed_preloads;
        size_t cache_hits_from_preload;
        double preload_effectiveness; // 预加载命中率
        std::chrono::milliseconds avg_preload_time;
    };
    PreloadStats get_preload_stats() const;

private:
    class Impl;
    std::unique_ptr<Impl> pimpl_;
};

// 模型版本管理器
class ModelVersionManager {
public:
    struct ModelVersion {
        std::string model_id;
        std::string version;
        std::string model_path;
        size_t model_size_mb;
        std::chrono::system_clock::time_point created_time;
        std::string checksum;
        bool is_active;
    };
    
    ModelVersionManager();
    ~ModelVersionManager();
    
    // 注册模型版本
    bool register_model_version(const ModelVersion& version);
    
    // 获取活跃版本
    std::optional<ModelVersion> get_active_version(const std::string& model_id) const;
    
    // 获取所有版本
    std::vector<ModelVersion> get_all_versions(const std::string& model_id) const;
    
    // 设置活跃版本
    bool set_active_version(const std::string& model_id, const std::string& version);
    
    // 删除版本
    bool remove_version(const std::string& model_id, const std::string& version);
    
    // 检查版本兼容性
    bool check_version_compatibility(const std::string& model_id, const std::string& version) const;
    
    // 获取版本升级建议
    std::vector<std::string> get_upgrade_recommendations() const;

private:
    class Impl;
    std::unique_ptr<Impl> pimpl_;
};

// 模型热更新管理器
class ModelHotReloader {
public:
    ModelHotReloader(ModelCache& cache, ModelVersionManager& version_manager);
    ~ModelHotReloader();
    
    // 启动热更新监控
    void start_monitoring(const std::string& models_directory);
    
    // 停止热更新监控
    void stop_monitoring();
    
    // 手动触发热更新
    bool trigger_hot_reload(const std::string& model_id);
    
    // 设置热更新策略
    enum class HotReloadStrategy {
        IMMEDIATE,    // 立即更新
        GRACEFUL,     // 优雅更新（等待当前任务完成）
        SCHEDULED     // 计划更新
    };
    void set_hot_reload_strategy(HotReloadStrategy strategy);
    
    // 注册热更新回调
    using HotReloadCallback = std::function<void(const std::string& model_id, bool success)>;
    void register_hot_reload_callback(const std::string& name, HotReloadCallback callback);
    
    // 获取热更新统计
    struct HotReloadStats {
        size_t total_reload_attempts;
        size_t successful_reloads;
        size_t failed_reloads;
        std::chrono::milliseconds avg_reload_time;
        size_t active_monitoring_paths;
    };
    HotReloadStats get_hot_reload_stats() const;

private:
    class Impl;
    std::unique_ptr<Impl> pimpl_;
};

// 模型性能分析器
class ModelPerformanceAnalyzer {
public:
    struct ModelPerformanceMetrics {
        std::string model_id;
        std::chrono::milliseconds avg_inference_time;
        std::chrono::milliseconds load_time;
        size_t memory_usage_mb;
        double cpu_utilization;
        double gpu_utilization;
        size_t inference_count;
        double throughput_per_second;
        double accuracy_score;
    };
    
    ModelPerformanceAnalyzer();
    ~ModelPerformanceAnalyzer();
    
    // 记录推理性能
    void record_inference_performance(
        const std::string& model_id,
        std::chrono::milliseconds inference_time,
        size_t input_size,
        size_t output_size
    );
    
    // 记录加载性能
    void record_load_performance(
        const std::string& model_id,
        std::chrono::milliseconds load_time,
        size_t memory_usage_mb
    );
    
    // 获取模型性能指标
    std::optional<ModelPerformanceMetrics> get_performance_metrics(const std::string& model_id) const;
    
    // 获取所有模型性能排名
    std::vector<ModelPerformanceMetrics> get_performance_ranking(
        bool by_speed = true
    ) const;
    
    // 生成性能报告
    std::string generate_performance_report() const;
    
    // 获取性能优化建议
    std::vector<std::string> get_optimization_suggestions(const std::string& model_id) const;

private:
    class Impl;
    std::unique_ptr<Impl> pimpl_;
};

} // namespace ai_assistant