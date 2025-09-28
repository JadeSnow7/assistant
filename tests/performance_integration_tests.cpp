#include "../include/optimized_model_engine.hpp"
#include "../include/benchmark_framework.hpp"
#include <gtest/gtest.h>
#include <chrono>
#include <thread>
#include <vector>

namespace ai_assistant {
namespace tests {

class PerformanceIntegrationTest : public ::testing::Test {
protected:
    void SetUp() override {
        engine_ = std::make_unique<OptimizedModelEngine>();
        benchmarker_ = std::make_unique<PerformanceBenchmarker>();
        stress_tester_ = std::make_unique<StressTester>();
        
        // 初始化引擎
        ASSERT_TRUE(engine_->initialize("test_config.yaml"));
        
        // 启动性能监控
        engine_->start_performance_monitoring(std::chrono::milliseconds(100));
    }
    
    void TearDown() override {
        engine_->stop_performance_monitoring();
    }

    std::unique_ptr<OptimizedModelEngine> engine_;
    std::unique_ptr<PerformanceBenchmarker> benchmarker_;
    std::unique_ptr<StressTester> stress_tester_;
};

// 基础性能测试
TEST_F(PerformanceIntegrationTest, BasicPerformanceTest) {
    // 创建测试请求
    OptimizedInferenceRequest request;
    request.prompt = "Hello, how are you today?";
    request.model_type = ModelType::LOCAL_SMALL;
    request.enable_gpu_acceleration = true;
    request.enable_caching = true;
    
    // 执行推理
    auto start_time = std::chrono::high_resolution_clock::now();
    auto response = engine_->inference(request);
    auto end_time = std::chrono::high_resolution_clock::now();
    
    // 验证响应
    EXPECT_FALSE(response.text.empty());
    EXPECT_TRUE(response.finished);
    EXPECT_GT(response.confidence, 0.0);
    
    // 验证性能指标
    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end_time - start_time);
    EXPECT_LT(duration.count(), 1000); // 应该在1秒内完成
    
    // 验证性能监控数据
    auto metrics = engine_->get_performance_metrics();
    EXPECT_GT(metrics.avg_response_time.count(), 0);
}

// GPU加速性能测试
TEST_F(PerformanceIntegrationTest, GPUAccelerationPerformanceTest) {
    // 测试GPU加速开启
    engine_->enable_gpu_acceleration(true);
    
    OptimizedInferenceRequest request;
    request.prompt = "Generate a detailed explanation of machine learning algorithms.";
    request.model_type = ModelType::LOCAL_SMALL;
    request.enable_gpu_acceleration = true;
    
    auto gpu_start = std::chrono::high_resolution_clock::now();
    auto gpu_response = engine_->inference(request);
    auto gpu_end = std::chrono::high_resolution_clock::now();
    auto gpu_duration = std::chrono::duration_cast<std::chrono::milliseconds>(gpu_end - gpu_start);
    
    // 测试GPU加速关闭
    engine_->enable_gpu_acceleration(false);
    request.enable_gpu_acceleration = false;
    
    auto cpu_start = std::chrono::high_resolution_clock::now();
    auto cpu_response = engine_->inference(request);
    auto cpu_end = std::chrono::high_resolution_clock::now();
    auto cpu_duration = std::chrono::duration_cast<std::chrono::milliseconds>(cpu_end - cpu_start);
    
    // GPU应该更快（如果可用）
    if (gpu_response.used_gpu) {
        EXPECT_LT(gpu_duration.count(), cpu_duration.count());
        std::cout << "GPU acceleration improvement: " 
                  << (double)cpu_duration.count() / gpu_duration.count() << "x" << std::endl;
    }
}

// 内存优化性能测试
TEST_F(PerformanceIntegrationTest, MemoryOptimizationTest) {
    // 获取初始内存状态
    auto initial_memory = engine_->get_memory_stats();
    
    // 执行多次推理以测试内存管理
    std::vector<OptimizedInferenceRequest> requests;
    for (int i = 0; i < 100; ++i) {
        OptimizedInferenceRequest request;
        request.prompt = "Test prompt " + std::to_string(i);
        request.session_id = "session_" + std::to_string(i % 10); // 10个不同会话
        requests.push_back(request);
    }
    
    // 批量执行推理
    auto responses = engine_->batch_inference(requests);
    EXPECT_EQ(responses.size(), requests.size());
    
    // 检查内存使用情况
    auto final_memory = engine_->get_memory_stats();
    
    // 内存碎片化应该保持在合理范围内
    EXPECT_LT(final_memory.fragmentation_ratio, 0.3);
    
    // 内存使用增长应该是可控的
    auto memory_growth = final_memory.used_size_mb - initial_memory.used_size_mb;
    EXPECT_LT(memory_growth, 500); // 不应该增长超过500MB
    
    std::cout << "Memory usage: " << initial_memory.used_size_mb 
              << "MB -> " << final_memory.used_size_mb << "MB" << std::endl;
    std::cout << "Fragmentation ratio: " << final_memory.fragmentation_ratio << std::endl;
}

// 异步处理性能测试
TEST_F(PerformanceIntegrationTest, AsyncProcessingPerformanceTest) {
    const size_t num_requests = 50;
    std::vector<std::future<OptimizedInferenceResponse>> futures;
    
    auto start_time = std::chrono::high_resolution_clock::now();
    
    // 提交异步任务
    for (size_t i = 0; i < num_requests; ++i) {
        OptimizedInferenceRequest request;
        request.prompt = "Async test prompt " + std::to_string(i);
        request.priority = (i % 3 == 0) ? TaskPriority::HIGH : TaskPriority::NORMAL;
        
        futures.push_back(engine_->inference_async(request));
    }
    
    // 等待所有任务完成
    size_t successful_responses = 0;
    for (auto& future : futures) {
        try {
            auto response = future.get();
            if (response.finished && !response.text.empty()) {
                successful_responses++;
            }
        } catch (const std::exception& e) {
            std::cerr << "Async task failed: " << e.what() << std::endl;
        }
    }
    
    auto end_time = std::chrono::high_resolution_clock::now();
    auto total_duration = std::chrono::duration_cast<std::chrono::milliseconds>(end_time - start_time);
    
    // 验证并发处理效果
    EXPECT_EQ(successful_responses, num_requests);
    EXPECT_LT(total_duration.count(), num_requests * 100); // 并发应该显著快于串行
    
    double avg_time_per_request = (double)total_duration.count() / num_requests;
    std::cout << "Async processing: " << num_requests << " requests in " 
              << total_duration.count() << "ms (avg: " << avg_time_per_request << "ms/req)" << std::endl;
}

// 模型缓存性能测试
TEST_F(PerformanceIntegrationTest, ModelCachePerformanceTest) {
    // 启用缓存
    engine_->enable_intelligent_caching(true);
    
    OptimizedInferenceRequest request;
    request.prompt = "Cache test prompt";
    request.session_id = "cache_test_session";
    request.enable_caching = true;
    
    // 第一次请求（应该未命中缓存）
    auto start1 = std::chrono::high_resolution_clock::now();
    auto response1 = engine_->inference(request);
    auto end1 = std::chrono::high_resolution_clock::now();
    auto duration1 = std::chrono::duration_cast<std::chrono::milliseconds>(end1 - start1);
    
    EXPECT_FALSE(response1.from_cache);
    
    // 第二次相同请求（应该命中缓存）
    auto start2 = std::chrono::high_resolution_clock::now();
    auto response2 = engine_->inference(request);
    auto end2 = std::chrono::high_resolution_clock::now();
    auto duration2 = std::chrono::duration_cast<std::chrono::milliseconds>(end2 - start2);
    
    // 缓存命中应该更快
    if (response2.from_cache) {
        EXPECT_LT(duration2.count(), duration1.count());
        std::cout << "Cache hit speedup: " 
                  << (double)duration1.count() / duration2.count() << "x" << std::endl;
    }
    
    // 检查缓存统计
    auto cache_stats = engine_->get_cache_stats();
    EXPECT_GT(cache_stats.total_models, 0);
    if (cache_stats.cache_hits > 0) {
        EXPECT_GT(cache_stats.hit_ratio, 0.0);
    }
}

// 压力测试
TEST_F(PerformanceIntegrationTest, StressTest) {
    StressTester::StressTestConfig config;
    config.max_concurrent_users = 20;
    config.test_duration = std::chrono::seconds(30);
    config.ramp_up_time = std::chrono::seconds(10);
    config.error_rate_threshold = 5.0;
    
    auto test_function = [this]() {
        OptimizedInferenceRequest request;
        request.prompt = "Stress test prompt for performance evaluation";
        request.timeout = std::chrono::milliseconds(5000);
        
        try {
            auto response = engine_->inference(request);
            if (!response.finished || response.text.empty()) {
                throw std::runtime_error("Invalid response");
            }
        } catch (const std::exception& e) {
            throw; // 重新抛出异常以便统计错误率
        }
    };
    
    auto result = stress_tester_->run_stress_test(test_function, config, "Engine Stress Test");
    
    // 验证压力测试结果
    EXPECT_LT(result.error_rate_percent, config.error_rate_threshold);
    EXPECT_GT(result.successful_requests, 0);
    EXPECT_LT(result.avg_response_time.count(), 2000); // 平均响应时间应该小于2秒
    
    std::cout << "Stress test results:" << std::endl;
    std::cout << "  Total requests: " << result.total_requests << std::endl;
    std::cout << "  Successful requests: " << result.successful_requests << std::endl;
    std::cout << "  Error rate: " << result.error_rate_percent << "%" << std::endl;
    std::cout << "  Avg response time: " << result.avg_response_time.count() << "ms" << std::endl;
    std::cout << "  Max RPS: " << result.max_requests_per_second << std::endl;
}

// 瓶颈分析测试
TEST_F(PerformanceIntegrationTest, BottleneckAnalysisTest) {
    // 运行一段时间以收集性能数据
    std::vector<std::future<OptimizedInferenceResponse>> futures;
    
    for (int i = 0; i < 30; ++i) {
        OptimizedInferenceRequest request;
        request.prompt = "Bottleneck analysis test prompt " + std::to_string(i);
        futures.push_back(engine_->inference_async(request));
        
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }
    
    // 等待所有任务完成
    for (auto& future : futures) {
        future.wait();
    }
    
    // 执行瓶颈分析
    auto bottleneck_analysis = engine_->analyze_performance_bottlenecks();
    
    // 验证瓶颈分析结果
    EXPECT_GE(bottleneck_analysis.severity_score, 0.0);
    EXPECT_LE(bottleneck_analysis.severity_score, 1.0);
    EXPECT_FALSE(bottleneck_analysis.description.empty());
    EXPECT_FALSE(bottleneck_analysis.recommendations.empty());
    
    std::cout << "Bottleneck analysis:" << std::endl;
    std::cout << "  Primary bottleneck: " << static_cast<int>(bottleneck_analysis.primary_bottleneck) << std::endl;
    std::cout << "  Severity score: " << bottleneck_analysis.severity_score << std::endl;
    std::cout << "  Description: " << bottleneck_analysis.description << std::endl;
    std::cout << "  Recommendations:" << std::endl;
    for (const auto& rec : bottleneck_analysis.recommendations) {
        std::cout << "    - " << rec << std::endl;
    }
}

// 自动性能调优测试
TEST_F(PerformanceIntegrationTest, AutoTuningTest) {
    // 获取调优前的性能指标
    auto metrics_before = engine_->get_performance_metrics();
    
    // 执行自动调优
    bool tuning_result = engine_->auto_tune_performance();
    EXPECT_TRUE(tuning_result);
    
    // 运行一些负载以测试调优效果
    std::vector<OptimizedInferenceRequest> requests;
    for (int i = 0; i < 20; ++i) {
        OptimizedInferenceRequest request;
        request.prompt = "Auto tuning test prompt " + std::to_string(i);
        requests.push_back(request);
    }
    
    auto start_time = std::chrono::high_resolution_clock::now();
    auto responses = engine_->batch_inference(requests);
    auto end_time = std::chrono::high_resolution_clock::now();
    
    EXPECT_EQ(responses.size(), requests.size());
    
    // 验证所有响应都成功
    for (const auto& response : responses) {
        EXPECT_TRUE(response.finished);
        EXPECT_FALSE(response.text.empty());
    }
    
    auto total_time = std::chrono::duration_cast<std::chrono::milliseconds>(end_time - start_time);
    double avg_time_per_request = (double)total_time.count() / requests.size();
    
    std::cout << "Auto-tuning test: " << requests.size() << " requests in " 
              << total_time.count() << "ms (avg: " << avg_time_per_request << "ms/req)" << std::endl;
}

// 综合性能基准测试
TEST_F(PerformanceIntegrationTest, ComprehensiveBenchmark) {
    // 运行完整的性能基准测试
    auto benchmark_result = engine_->run_performance_benchmark();
    
    // 验证基准测试结果
    EXPECT_GT(benchmark_result.total_iterations, 0);
    EXPECT_GT(benchmark_result.successful_iterations, 0);
    EXPECT_GE(benchmark_result.success_rate, 0.95); // 成功率应该至少95%
    EXPECT_GT(benchmark_result.requests_per_second, 0);
    
    // 验证性能指标在合理范围内
    EXPECT_LT(benchmark_result.avg_time.count(), 1000); // 平均响应时间应该小于1秒
    EXPECT_LT(benchmark_result.p95_time.count(), 2000); // P95响应时间应该小于2秒
    EXPECT_LT(benchmark_result.p99_time.count(), 3000); // P99响应时间应该小于3秒
    
    std::cout << "Comprehensive benchmark results:" << std::endl;
    std::cout << "  Total iterations: " << benchmark_result.total_iterations << std::endl;
    std::cout << "  Success rate: " << benchmark_result.success_rate << std::endl;
    std::cout << "  Requests per second: " << benchmark_result.requests_per_second << std::endl;
    std::cout << "  Average response time: " << benchmark_result.avg_time.count() << "ms" << std::endl;
    std::cout << "  P95 response time: " << benchmark_result.p95_time.count() << "ms" << std::endl;
    std::cout << "  P99 response time: " << benchmark_result.p99_time.count() << "ms" << std::endl;
    
    // 生成详细的性能报告
    auto performance_report = engine_->generate_performance_report();
    EXPECT_FALSE(performance_report.empty());
    
    std::cout << "Performance Report:" << std::endl;
    std::cout << performance_report << std::endl;
}

} // namespace tests
} // namespace ai_assistant

// 主函数
int main(int argc, char** argv) {
    ::testing::InitGoogleTest(&argc, argv);
    
    std::cout << "Starting Performance Integration Tests..." << std::endl;
    std::cout << "=========================================" << std::endl;
    
    int result = RUN_ALL_TESTS();
    
    std::cout << "=========================================" << std::endl;
    std::cout << "Performance Integration Tests Completed." << std::endl;
    
    return result;
}