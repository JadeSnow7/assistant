#pragma once

#include "common.hpp"
#include "performance_analyzer.hpp"
#include <vector>
#include <chrono>
#include <functional>
#include <future>
#include <thread>

namespace ai_assistant {

// 基准测试结果
struct BenchmarkResult {
    std::string test_name;
    size_t total_iterations;
    size_t successful_iterations;
    size_t failed_iterations;
    std::chrono::milliseconds total_time;
    std::chrono::milliseconds min_time;
    std::chrono::milliseconds max_time;
    std::chrono::milliseconds avg_time;
    std::chrono::milliseconds median_time;
    std::chrono::milliseconds p95_time;
    std::chrono::milliseconds p99_time;
    double requests_per_second;
    double success_rate;
    std::vector<std::chrono::milliseconds> response_times;
};

// 压力测试结果
struct StressTestResult {
    std::string test_name;
    size_t max_concurrent_users;
    std::chrono::seconds test_duration;
    std::chrono::seconds ramp_up_time;
    size_t total_requests;
    size_t successful_requests;
    size_t failed_requests;
    double max_requests_per_second;
    double avg_requests_per_second;
    std::chrono::milliseconds avg_response_time;
    double error_rate_percent;
    std::vector<PerformanceMetrics> metrics_timeline;
    std::string bottleneck_analysis;
};

// 内存基准测试结果
struct MemoryBenchmarkResult {
    std::string test_name;
    size_t peak_memory_mb;
    size_t avg_memory_mb;
    size_t min_memory_mb;
    double fragmentation_ratio;
    size_t allocation_count;
    size_t deallocation_count;
    std::chrono::milliseconds total_test_time;
    double allocations_per_second;
    std::vector<size_t> memory_timeline;
};

// 性能基准测试器
class PerformanceBenchmarker {
public:
    PerformanceBenchmarker();
    ~PerformanceBenchmarker();
    
    // 响应时间基准测试
    BenchmarkResult benchmark_response_time(
        std::function<void()> test_function,
        size_t iterations = 1000,
        const std::string& test_name = "Response Time Benchmark"
    );
    
    // 并发性能基准测试
    BenchmarkResult benchmark_concurrency(
        std::function<void()> test_function,
        size_t concurrent_threads = 10,
        size_t iterations_per_thread = 100,
        const std::string& test_name = "Concurrency Benchmark"
    );
    
    // 吞吐量基准测试
    BenchmarkResult benchmark_throughput(
        std::function<void()> test_function,
        std::chrono::seconds test_duration = std::chrono::seconds(60),
        const std::string& test_name = "Throughput Benchmark"
    );
    
    // 内存使用基准测试
    MemoryBenchmarkResult benchmark_memory_usage(
        std::function<void()> test_function,
        std::chrono::seconds duration = std::chrono::seconds(60),
        const std::string& test_name = "Memory Usage Benchmark"
    );
    
    // 延迟分析基准测试
    BenchmarkResult benchmark_latency_analysis(
        std::function<void()> test_function,
        size_t iterations = 10000,
        const std::string& test_name = "Latency Analysis Benchmark"
    );
    
    // 批量测试
    std::vector<BenchmarkResult> run_benchmark_suite(
        const std::vector<std::pair<std::string, std::function<void()>>>& test_cases
    );
    
    // 导出基准测试报告
    bool export_benchmark_report(
        const std::vector<BenchmarkResult>& results,
        const std::string& file_path
    ) const;

private:
    class Impl;
    std::unique_ptr<Impl> pimpl_;
};

// 压力测试器
class StressTester {
public:
    // 压力测试配置
    struct StressTestConfig {
        size_t max_concurrent_users = 100;
        std::chrono::seconds ramp_up_time{60};
        std::chrono::seconds test_duration{300};
        std::chrono::seconds ramp_down_time{30};
        std::chrono::milliseconds think_time{100};
        double error_rate_threshold = 5.0; // 百分比
        size_t max_requests_per_second = 1000;
        bool enable_real_time_monitoring = true;
    };
    
    StressTester();
    ~StressTester();
    
    // 运行压力测试
    StressTestResult run_stress_test(
        std::function<void()> test_function,
        const StressTestConfig& config,
        const std::string& test_name = "Stress Test"
    );
    
    // 运行负载测试
    StressTestResult run_load_test(
        std::function<void()> test_function,
        size_t constant_load,
        std::chrono::seconds duration,
        const std::string& test_name = "Load Test"
    );
    
    // 运行峰值测试
    StressTestResult run_spike_test(
        std::function<void()> test_function,
        size_t base_load,
        size_t spike_load,
        std::chrono::seconds spike_duration,
        const std::string& test_name = "Spike Test"
    );
    
    // 运行容量测试
    StressTestResult run_volume_test(
        std::function<void()> test_function,
        size_t data_volume_mb,
        const std::string& test_name = "Volume Test"
    );
    
    // 运行稳定性测试
    StressTestResult run_stability_test(
        std::function<void()> test_function,
        std::chrono::hours test_duration,
        const std::string& test_name = "Stability Test"
    );
    
    // 设置性能监控器
    void set_performance_monitor(std::shared_ptr<PerformanceAnalyzer> monitor);
    
    // 获取实时测试状态
    struct TestStatus {
        bool is_running;
        std::chrono::seconds elapsed_time;
        size_t current_concurrent_users;
        size_t total_requests;
        size_t successful_requests;
        size_t failed_requests;
        double current_rps;
        std::chrono::milliseconds avg_response_time;
        double error_rate;
    };
    TestStatus get_test_status() const;
    
    // 停止正在运行的测试
    void stop_current_test();

private:
    class Impl;
    std::unique_ptr<Impl> pimpl_;
};

// AI模型专用基准测试器
class AIModelBenchmarker {
public:
    // 推理性能测试
    struct InferenceTestConfig {
        std::vector<std::string> test_prompts;
        size_t iterations_per_prompt = 100;
        size_t concurrent_requests = 10;
        bool measure_memory_usage = true;
        bool measure_gpu_usage = true;
        std::chrono::seconds max_inference_time{30};
    };
    
    struct InferenceTestResult {
        std::string prompt;
        size_t total_inferences;
        size_t successful_inferences;
        std::chrono::milliseconds avg_inference_time;
        std::chrono::milliseconds min_inference_time;
        std::chrono::milliseconds max_inference_time;
        size_t avg_memory_usage_mb;
        double avg_gpu_utilization;
        double success_rate;
        size_t total_tokens_generated;
        double tokens_per_second;
    };
    
    AIModelBenchmarker();
    ~AIModelBenchmarker();
    
    // 推理性能基准测试
    std::vector<InferenceTestResult> benchmark_inference_performance(
        std::function<InferenceResponse(const InferenceRequest&)> inference_function,
        const InferenceTestConfig& config
    );
    
    // 模型加载性能测试
    struct ModelLoadTestResult {
        std::string model_path;
        std::chrono::milliseconds load_time;
        size_t model_size_mb;
        size_t memory_usage_after_load_mb;
        bool load_successful;
        std::string error_message;
    };
    
    std::vector<ModelLoadTestResult> benchmark_model_loading(
        std::function<bool(const std::string&)> load_function,
        const std::vector<std::string>& model_paths
    );
    
    // 批量推理测试
    BenchmarkResult benchmark_batch_inference(
        std::function<std::vector<InferenceResponse>(const std::vector<InferenceRequest>&)> batch_function,
        const std::vector<std::vector<InferenceRequest>>& test_batches
    );
    
    // 并发推理压力测试
    StressTestResult stress_test_concurrent_inference(
        std::function<InferenceResponse(const InferenceRequest&)> inference_function,
        const std::vector<InferenceRequest>& test_requests,
        size_t max_concurrent_requests = 50
    );
    
    // GPU性能基准测试
    struct GPUBenchmarkResult {
        double avg_gpu_utilization;
        size_t avg_gpu_memory_usage_mb;
        double gpu_memory_efficiency;
        std::chrono::milliseconds gpu_warmup_time;
        double cuda_kernel_efficiency;
    };
    
    GPUBenchmarkResult benchmark_gpu_performance(
        std::function<void()> gpu_function,
        size_t iterations = 1000
    );

private:
    class Impl;
    std::unique_ptr<Impl> pimpl_;
};

// 测试数据生成器
class TestDataGenerator {
public:
    // 生成随机推理请求
    static std::vector<InferenceRequest> generate_inference_requests(
        size_t count,
        size_t min_prompt_length = 10,
        size_t max_prompt_length = 500
    );
    
    // 生成不同复杂度的测试用例
    static std::vector<InferenceRequest> generate_complexity_test_cases();
    
    // 生成性能测试负载模式
    static std::vector<size_t> generate_load_pattern(
        const std::string& pattern_type, // "ramp", "spike", "wave", "constant"
        size_t duration_seconds,
        size_t max_load
    );
    
    // 生成内存压力测试数据
    static std::vector<size_t> generate_memory_test_allocations(
        size_t total_size_mb,
        const std::string& pattern = "random"
    );

private:
    static std::string generate_random_text(size_t length);
    static std::vector<std::string> load_test_prompts_from_file(const std::string& file_path);
};

// 基准测试报告生成器
class BenchmarkReporter {
public:
    // 生成HTML报告
    static bool generate_html_report(
        const std::vector<BenchmarkResult>& benchmark_results,
        const std::vector<StressTestResult>& stress_results,
        const std::string& output_path
    );
    
    // 生成JSON报告
    static bool generate_json_report(
        const std::vector<BenchmarkResult>& benchmark_results,
        const std::vector<StressTestResult>& stress_results,
        const std::string& output_path
    );
    
    // 生成CSV报告
    static bool generate_csv_report(
        const std::vector<BenchmarkResult>& benchmark_results,
        const std::string& output_path
    );
    
    // 生成性能对比报告
    static bool generate_comparison_report(
        const std::vector<BenchmarkResult>& baseline_results,
        const std::vector<BenchmarkResult>& current_results,
        const std::string& output_path
    );
    
    // 生成优化建议报告
    static std::string generate_optimization_recommendations(
        const std::vector<BenchmarkResult>& results,
        const std::vector<StressTestResult>& stress_results
    );

private:
    static std::string format_duration(std::chrono::milliseconds duration);
    static std::string format_memory_size(size_t size_bytes);
    static std::string calculate_performance_grade(const BenchmarkResult& result);
};

} // namespace ai_assistant