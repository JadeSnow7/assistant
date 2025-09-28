#pragma once

#include "common.hpp"
#include <chrono>
#include <unordered_map>
#include <vector>
#include <memory>
#include <atomic>
#include <mutex>
#include <thread>
#include <functional>

namespace ai_assistant {

// 性能指标结构
struct PerformanceMetrics {
    std::chrono::steady_clock::time_point timestamp;
    double cpu_usage_percent;
    size_t memory_usage_mb;
    double gpu_usage_percent;
    size_t gpu_memory_mb;
    size_t active_sessions;
    std::chrono::milliseconds avg_response_time;
    size_t requests_per_second;
    double error_rate_percent;
    size_t concurrent_connections;
    double throughput_mbps;
};

// 性能快照
struct PerformanceSnapshot {
    PerformanceMetrics current;
    PerformanceMetrics peak;
    PerformanceMetrics average;
    std::chrono::minutes duration;
};

// 瓶颈类型枚举
enum class BottleneckType {
    CPU_BOUND,
    MEMORY_BOUND, 
    GPU_BOUND,
    IO_BOUND,
    NETWORK_BOUND,
    CONCURRENCY_BOUND,
    NONE
};

// 瓶颈分析结果
struct BottleneckAnalysis {
    BottleneckType primary_bottleneck;
    BottleneckType secondary_bottleneck;
    double severity_score;  // 0.0-1.0
    std::string description;
    std::vector<std::string> recommendations;
    std::unordered_map<std::string, double> resource_utilization;
};

// 性能阈值配置
struct PerformanceThresholds {
    double cpu_warning_threshold = 70.0;
    double cpu_critical_threshold = 90.0;
    double memory_warning_threshold = 75.0; 
    double memory_critical_threshold = 95.0;
    double gpu_warning_threshold = 80.0;
    double gpu_critical_threshold = 95.0;
    std::chrono::milliseconds response_time_warning{1000};
    std::chrono::milliseconds response_time_critical{3000};
    double error_rate_warning = 1.0;
    double error_rate_critical = 5.0;
};

// 性能分析器主类
class PerformanceAnalyzer {
public:
    PerformanceAnalyzer();
    ~PerformanceAnalyzer();

    // 启动性能分析
    bool start_analysis(std::chrono::milliseconds collection_interval = std::chrono::milliseconds(1000));
    
    // 停止性能分析
    void stop_analysis();
    
    // 获取当前性能指标
    PerformanceMetrics get_current_metrics() const;
    
    // 获取历史性能数据
    std::vector<PerformanceMetrics> get_historical_metrics(size_t count = 100) const;
    
    // 获取性能快照
    PerformanceSnapshot get_performance_snapshot(std::chrono::minutes duration) const;
    
    // 执行瓶颈分析
    BottleneckAnalysis analyze_bottlenecks() const;
    
    // 设置性能阈值
    void set_thresholds(const PerformanceThresholds& thresholds);
    
    // 获取性能阈值
    PerformanceThresholds get_thresholds() const;
    
    // 检查是否超过阈值
    std::vector<std::string> check_threshold_violations() const;
    
    // 导出性能报告
    bool export_performance_report(const std::string& file_path) const;
    
    // 注册性能事件回调
    using PerformanceCallback = std::function<void(const PerformanceMetrics&)>;
    void register_callback(const std::string& name, PerformanceCallback callback);
    
    // 注销性能事件回调
    void unregister_callback(const std::string& name);
    
    // 记录自定义性能事件
    void record_custom_event(const std::string& event_name, double value, const std::string& unit = "");
    
    // 开始性能计时
    void start_timer(const std::string& operation_name);
    
    // 结束性能计时
    std::chrono::milliseconds end_timer(const std::string& operation_name);
    
    // 获取操作统计信息
    struct OperationStats {
        size_t count;
        std::chrono::milliseconds total_time;
        std::chrono::milliseconds avg_time;
        std::chrono::milliseconds min_time;
        std::chrono::milliseconds max_time;
    };
    OperationStats get_operation_stats(const std::string& operation_name) const;
    
    // 清除统计数据
    void clear_statistics();
    
    // 获取系统建议
    std::vector<std::string> get_optimization_suggestions() const;

private:
    class Impl;
    std::unique_ptr<Impl> pimpl_;
};

// 性能基准测试工具
class PerformanceBenchmark {
public:
    struct BenchmarkResult {
        std::string test_name;
        size_t iterations;
        std::chrono::milliseconds total_time;
        std::chrono::milliseconds avg_time;
        std::chrono::milliseconds min_time;
        std::chrono::milliseconds max_time;
        double requests_per_second;
        double success_rate;
        std::vector<std::chrono::milliseconds> percentiles; // P50, P90, P95, P99
    };
    
    // 运行响应时间基准测试
    static BenchmarkResult benchmark_response_time(
        std::function<void()> test_function,
        size_t iterations = 1000,
        const std::string& test_name = "Response Time Test"
    );
    
    // 运行并发基准测试
    static BenchmarkResult benchmark_concurrency(
        std::function<void()> test_function,
        size_t concurrent_threads = 10,
        size_t iterations_per_thread = 100,
        const std::string& test_name = "Concurrency Test"
    );
    
    // 运行内存使用基准测试
    struct MemoryBenchmarkResult {
        std::string test_name;
        size_t peak_memory_mb;
        size_t avg_memory_mb;
        double fragmentation_ratio;
        size_t allocation_count;
        size_t deallocation_count;
    };
    
    static MemoryBenchmarkResult benchmark_memory_usage(
        std::function<void()> test_function,
        std::chrono::seconds duration = std::chrono::seconds(60),
        const std::string& test_name = "Memory Usage Test"
    );
    
    // 运行压力测试
    struct StressTestResult {
        std::string test_name;
        size_t max_concurrent_users;
        std::chrono::seconds test_duration;
        double max_requests_per_second;
        double avg_response_time_ms;
        double error_rate_percent;
        std::vector<PerformanceMetrics> metrics_timeline;
    };
    
    static StressTestResult run_stress_test(
        std::function<void()> test_function,
        size_t max_users = 200,
        std::chrono::seconds ramp_up_time = std::chrono::seconds(60),
        std::chrono::seconds test_duration = std::chrono::seconds(300),
        const std::string& test_name = "Stress Test"
    );
};

// RAII性能计时器
class ScopedTimer {
public:
    ScopedTimer(PerformanceAnalyzer& analyzer, const std::string& operation_name);
    ~ScopedTimer();
    
    // 获取已经过的时间
    std::chrono::milliseconds elapsed() const;

private:
    PerformanceAnalyzer& analyzer_;
    std::string operation_name_;
    std::chrono::steady_clock::time_point start_time_;
};

// 性能监控宏
#define PERF_TIMER(analyzer, name) ScopedTimer timer(analyzer, name)
#define PERF_MEASURE(analyzer, name, block) \
    do { \
        ScopedTimer timer(analyzer, name); \
        block; \
    } while(0)

} // namespace ai_assistant