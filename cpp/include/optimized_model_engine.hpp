#pragma once

#include "model_engine.hpp"
#include "performance_analyzer.hpp"
#include "gpu_engine.hpp"
#include "memory_optimizer.hpp"
#include "async_scheduler.hpp"
#include "model_cache.hpp"
#include "benchmark_framework.hpp"
#include <memory>
#include <vector>
#include <string>
#include <future>
#include <functional>

namespace ai_assistant {

// 扩展推理请求结构
struct OptimizedInferenceRequest : public InferenceRequest {
    TaskPriority priority = TaskPriority::NORMAL;
    bool enable_gpu_acceleration = true;
    bool enable_caching = true;
    size_t batch_size = 1;
    std::chrono::milliseconds timeout{30000};
};

// 扩展推理响应结构
struct OptimizedInferenceResponse : public InferenceResponse {
    bool used_gpu = false;
    bool from_cache = false;
    PerformanceMetrics performance_metrics;
    std::string optimization_info;
};

// 优化后的模型引擎类
class OptimizedModelEngine {
public:
    OptimizedModelEngine();
    ~OptimizedModelEngine();

    // 初始化引擎（包含所有性能优化）
    bool initialize(const std::string& config_path);
    
    // 同步推理（GPU加速 + 内存优化）
    OptimizedInferenceResponse inference(const OptimizedInferenceRequest& request);
    
    // 异步推理（任务调度优化）
    std::future<OptimizedInferenceResponse> inference_async(const OptimizedInferenceRequest& request);
    
    // 批量推理（GPU批处理优化）
    std::vector<OptimizedInferenceResponse> batch_inference(const std::vector<OptimizedInferenceRequest>& requests);
    
    // 流式推理（异步流处理）
    void inference_stream(const OptimizedInferenceRequest& request, 
                         std::function<void(const OptimizedInferenceResponse&)> callback);
    
    // 加载本地模型（智能缓存）
    bool load_local_model(const std::string& model_path);
    
    // 预加载常用模型
    std::vector<std::future<bool>> preload_models(const std::vector<std::string>& model_paths);
    
    // 设置云端API配置
    void set_cloud_config(const std::string& api_key, const std::string& endpoint);
    
    // 获取模型信息
    std::vector<std::string> get_available_models() const;
    
    // 健康检查（包含性能指标）
    bool is_healthy() const;
    
    // 获取性能统计
    PerformanceMetrics get_performance_metrics() const;
    
    // 获取GPU统计
    GPUModelEngine::GPUStats get_gpu_stats() const;
    
    // 获取内存统计
    HighPerformanceMemoryPool::MemoryStats get_memory_stats() const;
    
    // 获取缓存统计
    ModelCacheStats get_cache_stats() const;
    
    // 启用/禁用GPU加速
    void enable_gpu_acceleration(bool enable = true);
    
    // 启用/禁用智能缓存
    void enable_intelligent_caching(bool enable = true);
    
    // 设置性能优化级别
    enum class OptimizationLevel {
        MINIMAL,    // 最小优化
        BALANCED,   // 平衡优化
        AGGRESSIVE  // 激进优化
    };
    void set_optimization_level(OptimizationLevel level);
    
    // 获取优化建议
    std::vector<std::string> get_optimization_suggestions() const;
    
    // 运行性能基准测试
    BenchmarkResult run_performance_benchmark();
    
    // 启动性能监控
    void start_performance_monitoring(std::chrono::milliseconds interval = std::chrono::milliseconds(1000));
    
    // 停止性能监控
    void stop_performance_monitoring();
    
    // 执行性能瓶颈分析
    BottleneckAnalysis analyze_performance_bottlenecks() const;
    
    // 自动性能调优
    bool auto_tune_performance();
    
    // 获取详细的性能报告
    std::string generate_performance_report() const;

private:
    class Impl;
    std::unique_ptr<Impl> pimpl_;
};

// 性能优化管理器
class PerformanceOptimizationManager {
public:
    PerformanceOptimizationManager();
    ~PerformanceOptimizationManager();
    
    // 初始化优化管理器
    bool initialize(OptimizedModelEngine& engine);
    
    // 启动自动优化
    void start_auto_optimization(std::chrono::minutes check_interval = std::chrono::minutes(5));
    
    // 停止自动优化
    void stop_auto_optimization();
    
    // 手动触发优化
    bool trigger_optimization();
    
    // 获取优化历史
    struct OptimizationRecord {
        std::chrono::steady_clock::time_point timestamp;
        std::string optimization_type;
        std::string description;
        PerformanceMetrics before_metrics;
        PerformanceMetrics after_metrics;
        double improvement_ratio;
        bool success;
    };
    std::vector<OptimizationRecord> get_optimization_history() const;
    
    // 设置优化策略
    enum class OptimizationStrategy {
        PERFORMANCE_FIRST,  // 性能优先
        MEMORY_FIRST,       // 内存优先
        BALANCED,           // 平衡策略
        ENERGY_EFFICIENT    // 节能策略
    };
    void set_optimization_strategy(OptimizationStrategy strategy);
    
    // 导出优化配置
    bool export_optimization_config(const std::string& file_path) const;
    
    // 导入优化配置
    bool import_optimization_config(const std::string& file_path);

private:
    class Impl;
    std::unique_ptr<Impl> pimpl_;
};

// 智能负载均衡器
class IntelligentLoadBalancer {
public:
    struct WorkerNode {
        std::string id;
        std::string address;
        double cpu_usage;
        double memory_usage;
        double gpu_usage;
        size_t active_tasks;
        std::chrono::milliseconds avg_response_time;
        double health_score;
        bool is_available;
    };
    
    IntelligentLoadBalancer();
    ~IntelligentLoadBalancer();
    
    // 添加工作节点
    bool add_worker_node(const WorkerNode& node);
    
    // 移除工作节点
    bool remove_worker_node(const std::string& node_id);
    
    // 选择最优工作节点
    std::string select_optimal_worker(const OptimizedInferenceRequest& request);
    
    // 获取负载均衡统计
    struct LoadBalanceStats {
        size_t total_nodes;
        size_t available_nodes;
        size_t total_requests;
        std::unordered_map<std::string, size_t> requests_per_node;
        double avg_response_time_ms;
        double load_distribution_variance;
    };
    LoadBalanceStats get_load_balance_stats() const;
    
    // 设置负载均衡策略
    enum class BalanceStrategy {
        ROUND_ROBIN,        // 轮询
        LEAST_CONNECTIONS,  // 最少连接
        WEIGHTED_RESPONSE,  // 加权响应时间
        INTELLIGENT         // 智能选择
    };
    void set_balance_strategy(BalanceStrategy strategy);
    
    // 启动健康检查
    void start_health_check(std::chrono::seconds interval = std::chrono::seconds(30));
    
    // 停止健康检查
    void stop_health_check();

private:
    class Impl;
    std::unique_ptr<Impl> pimpl_;
};

// 性能优化配置
struct PerformanceOptimizationConfig {
    bool enable_gpu_acceleration = true;
    bool enable_memory_pool = true;
    bool enable_model_cache = true;
    bool enable_async_processing = true;
    bool enable_batch_processing = true;
    bool enable_load_balancing = false;
    
    size_t memory_pool_size_mb = 2048;
    size_t model_cache_size_mb = 4096;
    size_t thread_pool_size = std::thread::hardware_concurrency();
    size_t max_batch_size = 32;
    
    OptimizedModelEngine::OptimizationLevel optimization_level = 
        OptimizedModelEngine::OptimizationLevel::BALANCED;
    
    std::chrono::milliseconds performance_monitoring_interval{1000};
    std::chrono::minutes auto_optimization_interval{5};
    
    double cpu_usage_threshold = 80.0;
    double memory_usage_threshold = 85.0;
    double gpu_usage_threshold = 90.0;
};

} // namespace ai_assistant