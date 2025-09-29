#pragma once

#include "../core/async_types.hpp"
#include "../platform_config.h"

#ifdef HUSHELL_ENABLE_TESTING

#include <gtest/gtest.h>
#include <gmock/gmock.h>
#include <memory>
#include <string>
#include <vector>
#include <chrono>
#include <functional>
#include <future>
#include <thread>
#include <filesystem>
#include <random>

namespace hushell::testing {

    /**
     * @brief 测试配置
     */
    struct TestConfig {
        std::string test_name;
        std::chrono::milliseconds timeout = std::chrono::milliseconds(30000);
        bool enable_logging = true;
        bool enable_performance_tracking = true;
        std::string temp_dir = "/tmp/hushell_tests";
        size_t max_memory_mb = 1024;
        bool cleanup_after_test = true;
    };

    /**
     * @brief 性能测试结果
     */
    struct PerformanceResult {
        std::chrono::nanoseconds execution_time{0};
        size_t memory_usage_bytes = 0;
        size_t memory_peak_bytes = 0;
        double cpu_usage_percent = 0.0;
        size_t allocations_count = 0;
        std::string test_name;
        std::chrono::steady_clock::time_point timestamp;
    };

    /**
     * @brief 基准测试信息
     */
    struct BenchmarkInfo {
        std::string name;
        std::function<void()> benchmark_func;
        size_t iterations = 1000;
        std::chrono::milliseconds timeout = std::chrono::milliseconds(60000);
        bool warmup = true;
        size_t warmup_iterations = 100;
    };

    /**
     * @brief 测试基类 - 提供通用测试功能
     */
    class TestBase : public ::testing::Test {
    public:
        explicit TestBase(const TestConfig& config = {});
        virtual ~TestBase() = default;

    protected:
        void SetUp() override;
        void TearDown() override;

        // ========== 断言扩展 ==========

        /**
         * @brief 异步任务断言
         */
        template<typename T>
        void ASSERT_TASK_SUCCESS(const core::Task<core::Result<T>>& task) {
            auto result = task.get();
            ASSERT_TRUE(result.is_success()) << "Task failed: " << result.error_message();
        }

        template<typename T>
        void EXPECT_TASK_SUCCESS(const core::Task<core::Result<T>>& task) {
            auto result = task.get();
            EXPECT_TRUE(result.is_success()) << "Task failed: " << result.error_message();
        }

        /**
         * @brief 性能断言
         */
        void ASSERT_EXECUTION_TIME_LESS_THAN(std::function<void()> func, 
                                            std::chrono::milliseconds max_time);

        void EXPECT_EXECUTION_TIME_LESS_THAN(std::function<void()> func, 
                                           std::chrono::milliseconds max_time);

        /**
         * @brief 内存使用断言
         */
        void ASSERT_MEMORY_USAGE_LESS_THAN(std::function<void()> func, size_t max_bytes);
        void EXPECT_MEMORY_USAGE_LESS_THAN(std::function<void()> func, size_t max_bytes);

        // ========== 工具方法 ==========

        /**
         * @brief 创建临时文件
         */
        std::filesystem::path create_temp_file(const std::string& content = "");

        /**
         * @brief 创建临时目录
         */
        std::filesystem::path create_temp_directory();

        /**
         * @brief 生成随机数据
         */
        std::vector<uint8_t> generate_random_data(size_t size);
        std::string generate_random_string(size_t length);

        /**
         * @brief 等待条件满足
         */
        bool wait_for_condition(std::function<bool()> condition, 
                               std::chrono::milliseconds timeout = std::chrono::milliseconds(5000));

        /**
         * @brief 模拟延迟
         */
        void simulate_delay(std::chrono::milliseconds delay);

        /**
         * @brief 测量执行时间
         */
        template<typename F>
        std::chrono::nanoseconds measure_execution_time(F&& func) {
            auto start = std::chrono::high_resolution_clock::now();
            func();
            auto end = std::chrono::high_resolution_clock::now();
            return std::chrono::duration_cast<std::chrono::nanoseconds>(end - start);
        }

        /**
         * @brief 获取性能测试结果
         */
        PerformanceResult get_performance_result() const;

        /**
         * @brief 记录性能基准
         */
        void record_benchmark(const std::string& name, std::chrono::nanoseconds time);

    private:
        TestConfig config_;
        std::vector<std::filesystem::path> temp_files_;
        std::vector<std::filesystem::path> temp_directories_;
        std::chrono::steady_clock::time_point test_start_time_;
        size_t initial_memory_usage_;
        std::mt19937 random_generator_;

        void cleanup_temp_files();
        size_t get_current_memory_usage();
    };

    /**
     * @brief 异步测试基类
     */
    class AsyncTestBase : public TestBase {
    public:
        explicit AsyncTestBase(const TestConfig& config = {});
        virtual ~AsyncTestBase() = default;

    protected:
        void SetUp() override;
        void TearDown() override;

        // ========== 异步测试工具 ==========

        /**
         * @brief 运行异步测试
         */
        template<typename F>
        auto run_async_test(F&& test_func) -> decltype(test_func()) {
            return test_func().get();
        }

        /**
         * @brief 并发测试
         */
        template<typename F>
        void run_concurrent_test(F&& test_func, size_t thread_count) {
            std::vector<std::future<void>> futures;
            futures.reserve(thread_count);

            for (size_t i = 0; i < thread_count; ++i) {
                futures.emplace_back(std::async(std::launch::async, [test_func, i]() {
                    test_func(i);
                }));
            }

            for (auto& future : futures) {
                future.get();
            }
        }

        /**
         * @brief 超时测试
         */
        template<typename F>
        bool run_with_timeout(F&& func, std::chrono::milliseconds timeout) {
            auto future = std::async(std::launch::async, std::forward<F>(func));
            return future.wait_for(timeout) == std::future_status::ready;
        }

    private:
        std::unique_ptr<std::thread> async_runner_;
    };

    /**
     * @brief 性能测试基类
     */
    class PerformanceTestBase : public TestBase {
    public:
        explicit PerformanceTestBase(const TestConfig& config = {});
        virtual ~PerformanceTestBase() = default;

    protected:
        void SetUp() override;
        void TearDown() override;

        // ========== 基准测试 ==========

        /**
         * @brief 注册基准测试
         */
        void register_benchmark(const BenchmarkInfo& info);

        /**
         * @brief 运行所有基准测试
         */
        void run_all_benchmarks();

        /**
         * @brief 运行单个基准测试
         */
        PerformanceResult run_benchmark(const BenchmarkInfo& info);

        /**
         * @brief 压力测试
         */
        void run_stress_test(std::function<void()> func, 
                           std::chrono::seconds duration,
                           size_t max_concurrent_operations = 10);

        /**
         * @brief 内存泄漏测试
         */
        void run_memory_leak_test(std::function<void()> func, size_t iterations = 1000);

        /**
         * @brief 吞吐量测试
         */
        double measure_throughput(std::function<void()> func, 
                                std::chrono::seconds duration = std::chrono::seconds(10));

        // ========== 性能断言 ==========

        void ASSERT_THROUGHPUT_GREATER_THAN(std::function<void()> func, double min_ops_per_second);
        void EXPECT_THROUGHPUT_GREATER_THAN(std::function<void()> func, double min_ops_per_second);

        void ASSERT_LATENCY_LESS_THAN(std::function<void()> func, std::chrono::nanoseconds max_latency);
        void EXPECT_LATENCY_LESS_THAN(std::function<void()> func, std::chrono::nanoseconds max_latency);

    private:
        std::vector<BenchmarkInfo> benchmarks_;
        std::vector<PerformanceResult> results_;
    };

    /**
     * @brief Mock对象基类
     */
    template<typename Interface>
    class MockBase : public Interface {
    public:
        virtual ~MockBase() = default;

        // 通用Mock方法
        MOCK_METHOD(void, reset_mock, (), ());
        MOCK_METHOD(void, verify_mock, (), ());
    };

    /**
     * @brief 测试数据生成器
     */
    class TestDataGenerator {
    public:
        static TestDataGenerator& instance();

        // ========== 基础数据生成 ==========

        std::string generate_uuid();
        std::string generate_email();
        std::string generate_phone_number();
        std::string generate_url();

        // ========== 数值数据生成 ==========

        int generate_random_int(int min = 0, int max = 100);
        double generate_random_double(double min = 0.0, double max = 1.0);
        float generate_random_float(float min = 0.0f, float max = 1.0f);

        // ========== 字符串数据生成 ==========

        std::string generate_random_string(size_t length, 
                                         const std::string& charset = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789");
        std::string generate_random_text(size_t word_count);
        std::string generate_json_string(size_t complexity = 5);

        // ========== 集合数据生成 ==========

        template<typename T>
        std::vector<T> generate_vector(size_t size, std::function<T()> generator) {
            std::vector<T> result;
            result.reserve(size);
            for (size_t i = 0; i < size; ++i) {
                result.push_back(generator());
            }
            return result;
        }

        std::vector<uint8_t> generate_binary_data(size_t size);

    private:
        TestDataGenerator() : rng_(std::random_device{}()) {}
        std::mt19937 rng_;
    };

    /**
     * @brief 测试环境管理器
     */
    class TestEnvironment : public ::testing::Environment {
    public:
        static TestEnvironment& instance();

        void SetUp() override;
        void TearDown() override;

        // ========== 环境配置 ==========

        void set_global_config(const std::string& key, const std::string& value);
        std::string get_global_config(const std::string& key, const std::string& default_value = "");

        void enable_memory_tracking(bool enable);
        void enable_performance_tracking(bool enable);

        // ========== 资源管理 ==========

        std::filesystem::path get_test_data_dir() const;
        std::filesystem::path get_temp_dir() const;
        std::filesystem::path get_output_dir() const;

        void cleanup_test_environment();

    private:
        TestEnvironment() = default;
        std::unordered_map<std::string, std::string> global_config_;
        std::filesystem::path test_data_dir_;
        std::filesystem::path temp_dir_;
        std::filesystem::path output_dir_;
        bool memory_tracking_enabled_ = false;
        bool performance_tracking_enabled_ = false;
    };

    /**
     * @brief 测试工具函数
     */
    namespace utils {

        /**
         * @brief 比较浮点数
         */
        bool almost_equal(double a, double b, double epsilon = 1e-9);
        bool almost_equal(float a, float b, float epsilon = 1e-6f);

        /**
         * @brief 文件比较
         */
        bool files_equal(const std::filesystem::path& file1, const std::filesystem::path& file2);

        /**
         * @brief 创建测试文件
         */
        std::filesystem::path create_test_file(const std::string& content, 
                                             const std::string& extension = ".txt");

        /**
         * @brief 捕获标准输出
         */
        class OutputCapture {
        public:
            OutputCapture();
            ~OutputCapture();
            std::string get_output() const;

        private:
            std::stringstream buffer_;
            std::streambuf* old_cout_;
        };

        /**
         * @brief 异常测试辅助
         */
        template<typename Exception, typename F>
        void assert_throws(F&& func, const std::string& expected_message = "") {
            bool exception_thrown = false;
            std::string actual_message;

            try {
                func();
            } catch (const Exception& e) {
                exception_thrown = true;
                actual_message = e.what();
            } catch (...) {
                FAIL() << "Expected " << typeid(Exception).name() << " but got different exception";
            }

            ASSERT_TRUE(exception_thrown) << "Expected exception " << typeid(Exception).name() << " was not thrown";

            if (!expected_message.empty()) {
                EXPECT_THAT(actual_message, ::testing::HasSubstr(expected_message));
            }
        }

        /**
         * @brief 时间测量辅助
         */
        class Timer {
        public:
            Timer();
            void start();
            void stop();
            void reset();
            std::chrono::nanoseconds elapsed() const;
            double elapsed_seconds() const;

        private:
            std::chrono::high_resolution_clock::time_point start_time_;
            std::chrono::high_resolution_clock::time_point end_time_;
            bool running_ = false;
        };

        /**
         * @brief 重试测试辅助
         */
        template<typename F>
        bool retry_until_success(F&& func, int max_attempts = 3, 
                               std::chrono::milliseconds delay = std::chrono::milliseconds(100)) {
            for (int attempt = 0; attempt < max_attempts; ++attempt) {
                try {
                    func();
                    return true;
                } catch (...) {
                    if (attempt == max_attempts - 1) {
                        throw;
                    }
                    std::this_thread::sleep_for(delay);
                }
            }
            return false;
        }
    }

    /**
     * @brief 测试宏定义
     */

    // 性能测试宏
    #define PERFORMANCE_TEST(test_case_name, test_name) \
        class test_case_name##_##test_name##_PerfTest : public PerformanceTestBase { \
        public: \
            test_case_name##_##test_name##_PerfTest() : PerformanceTestBase({}) {} \
        }; \
        TEST_F(test_case_name##_##test_name##_PerfTest, test_name)

    // 异步测试宏
    #define ASYNC_TEST(test_case_name, test_name) \
        class test_case_name##_##test_name##_AsyncTest : public AsyncTestBase { \
        public: \
            test_case_name##_##test_name##_AsyncTest() : AsyncTestBase({}) {} \
        }; \
        TEST_F(test_case_name##_##test_name##_AsyncTest, test_name)

    // 基准测试宏
    #define BENCHMARK_TEST(name, iterations) \
        void benchmark_##name(); \
        static bool benchmark_##name##_registered = []() { \
            /* 注册基准测试的逻辑 */ \
            return true; \
        }(); \
        void benchmark_##name()

    // 参数化性能测试宏
    #define PERFORMANCE_TEST_P(test_case_name, test_name) \
        class test_case_name##_##test_name##_PerfTest : public PerformanceTestBase, \
                                                       public ::testing::WithParamInterface<typename test_case_name::ParamType> { \
        public: \
            test_case_name##_##test_name##_PerfTest() : PerformanceTestBase({}) {} \
        }; \
        TEST_P(test_case_name##_##test_name##_PerfTest, test_name)

} // namespace hushell::testing

#endif // HUSHELL_ENABLE_TESTING