#include "../../include/nex/testing/test_framework.hpp"
#include "../../include/nex/core/async_types.hpp"
#include <vector>
#include <string>

using namespace hushell::core;
using namespace hushell::testing;

namespace {

    /**
     * @brief Task测试类
     */
    class TaskTest : public TestBase {
    protected:
        void SetUp() override {
            TestBase::SetUp();
        }
    };

    /**
     * @brief Result测试类
     */
    class ResultTest : public TestBase {
    protected:
        void SetUp() override {
            TestBase::SetUp();
        }
    };

    // ==================== Task 基础功能测试 ====================

    TEST_F(TaskTest, BasicTaskCreationAndExecution) {
        auto task = []() -> Task<int> {
            co_return 42;
        }();

        EXPECT_TRUE(task.is_ready());
        auto result = task.get();
        EXPECT_EQ(result, 42);
    }

    TEST_F(TaskTest, TaskWithVoidReturn) {
        bool executed = false;
        
        auto task = [&executed]() -> Task<void> {
            executed = true;
            co_return;
        }();

        task.get();
        EXPECT_TRUE(executed);
    }

    TEST_F(TaskTest, TaskWithException) {
        auto task = []() -> Task<int> {
            throw std::runtime_error("Test exception");
            co_return 42;
        }();

        EXPECT_THROW(task.get(), std::runtime_error);
    }

    ASYNC_TEST(TaskTest, AsyncTaskChaining) {
        auto task1 = []() -> Task<int> {
            co_return 10;
        }();

        auto task2 = [](int value) -> Task<int> {
            co_return value * 2;
        };

        auto chained_task = task1.then(task2);
        auto result = co_await chained_task;
        EXPECT_EQ(result, 20);
    }

    TEST_F(TaskTest, TaskTimeout) {
        auto task = []() -> Task<int> {
            // 模拟长时间运行的任务
            co_await sleep_for(std::chrono::milliseconds(100));
            co_return 42;
        }();

        auto timeout_result = task.timeout(std::chrono::milliseconds(50));
        auto result = timeout_result.get();
        EXPECT_FALSE(result.has_value()); // 应该超时
    }

    // ==================== Result 基础功能测试 ====================

    TEST_F(ResultTest, SuccessResult) {
        auto result = Result<int>::success(42);
        
        EXPECT_TRUE(result.is_success());
        EXPECT_FALSE(result.is_error());
        EXPECT_EQ(result.value(), 42);
        EXPECT_EQ(result.error_code(), ErrorCode::SUCCESS);
    }

    TEST_F(ResultTest, ErrorResult) {
        auto result = Result<int>::error(ErrorCode::INVALID_ARGUMENT, "Test error");
        
        EXPECT_FALSE(result.is_success());
        EXPECT_TRUE(result.is_error());
        EXPECT_EQ(result.error_code(), ErrorCode::INVALID_ARGUMENT);
        EXPECT_EQ(result.error_message(), "Test error");
        
        EXPECT_THROW(result.value(), std::runtime_error);
    }

    TEST_F(ResultTest, ResultAndThen) {
        auto success_result = Result<int>::success(10);
        
        auto chained_result = success_result.and_then([](int value) {
            return Result<std::string>::success(std::to_string(value * 2));
        });
        
        EXPECT_TRUE(chained_result.is_success());
        EXPECT_EQ(chained_result.value(), "20");
    }

    TEST_F(ResultTest, ResultAndThenWithError) {
        auto error_result = Result<int>::error(ErrorCode::INTERNAL_ERROR, "Original error");
        
        auto chained_result = error_result.and_then([](int value) {
            return Result<std::string>::success(std::to_string(value));
        });
        
        EXPECT_TRUE(chained_result.is_error());
        EXPECT_EQ(chained_result.error_code(), ErrorCode::INTERNAL_ERROR);
        EXPECT_EQ(chained_result.error_message(), "Original error");
    }

    TEST_F(ResultTest, ResultOrElse) {
        auto error_result = Result<int>::error(ErrorCode::INVALID_ARGUMENT, "Test error");
        
        auto recovered_result = error_result.or_else([](ErrorCode code, const std::string& message) {
            return Result<int>::success(999); // 恢复为默认值
        });
        
        EXPECT_TRUE(recovered_result.is_success());
        EXPECT_EQ(recovered_result.value(), 999);
    }

    TEST_F(ResultTest, ResultValueOr) {
        auto success_result = Result<int>::success(42);
        auto error_result = Result<int>::error(ErrorCode::INTERNAL_ERROR, "Error");
        
        EXPECT_EQ(success_result.value_or(999), 42);
        EXPECT_EQ(error_result.value_or(999), 999);
    }

    TEST_F(ResultTest, ResultMap) {
        auto result = Result<int>::success(10);
        
        auto mapped_result = result.map([](int value) {
            return value * 2.5; // int -> double
        });
        
        EXPECT_TRUE(mapped_result.is_success());
        EXPECT_DOUBLE_EQ(mapped_result.value(), 25.0);
    }

    TEST_F(ResultTest, VoidResult) {
        auto success_result = Result<void>::success();
        auto error_result = Result<void>::error(ErrorCode::NETWORK_ERROR, "Network failed");
        
        EXPECT_TRUE(success_result.is_success());
        EXPECT_TRUE(error_result.is_error());
        EXPECT_EQ(error_result.error_code(), ErrorCode::NETWORK_ERROR);
    }

    // ==================== 错误代码测试 ====================

    TEST_F(ResultTest, ErrorCodeToString) {
        EXPECT_EQ(error_code_to_string(ErrorCode::SUCCESS), "Success");
        EXPECT_EQ(error_code_to_string(ErrorCode::INVALID_ARGUMENT), "Invalid argument");
        EXPECT_EQ(error_code_to_string(ErrorCode::INTERNAL_ERROR), "Internal error");
        EXPECT_EQ(error_code_to_string(ErrorCode::NETWORK_ERROR), "Network error");
    }

    // ==================== 协程工具函数测试 ====================

    ASYNC_TEST(TaskTest, SleepFor) {
        auto start_time = std::chrono::steady_clock::now();
        
        co_await sleep_for(std::chrono::milliseconds(50));
        
        auto end_time = std::chrono::steady_clock::now();
        auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(end_time - start_time);
        
        EXPECT_GE(elapsed.count(), 45); // 允许一些时间误差
        EXPECT_LE(elapsed.count(), 100);
    }

    ASYNC_TEST(TaskTest, Yield) {
        bool after_yield = false;
        
        auto task = [&after_yield]() -> Task<void> {
            co_await yield();
            after_yield = true;
        }();
        
        // yield应该暂停执行，但最终会完成
        co_await task;
        EXPECT_TRUE(after_yield);
    }

    // ==================== 性能测试 ====================

    PERFORMANCE_TEST(TaskTest, TaskCreationPerformance) {
        const size_t iterations = 10000;
        
        auto start_time = std::chrono::high_resolution_clock::now();
        
        for (size_t i = 0; i < iterations; ++i) {
            auto task = []() -> Task<int> {
                co_return 42;
            }();
            volatile int result = task.get(); // 防止优化
            (void)result;
        }
        
        auto end_time = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end_time - start_time);
        
        // 每个Task创建应该在合理时间内完成
        double average_time_us = static_cast<double>(duration.count()) / iterations;
        EXPECT_LT(average_time_us, 100.0); // 平均每个任务小于100微秒
        
        record_benchmark("TaskCreation", std::chrono::nanoseconds(duration.count() / iterations));
    }

    PERFORMANCE_TEST(ResultTest, ResultChainingPerformance) {
        const size_t iterations = 100000;
        
        auto start_time = std::chrono::high_resolution_clock::now();
        
        for (size_t i = 0; i < iterations; ++i) {
            auto result = Result<int>::success(static_cast<int>(i))
                .and_then([](int x) { return Result<int>::success(x * 2); })
                .and_then([](int x) { return Result<int>::success(x + 1); })
                .map([](int x) { return x * 3; });
            
            volatile int final_result = result.value();
            (void)final_result;
        }
        
        auto end_time = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::nanoseconds>(end_time - start_time);
        
        double average_time_ns = static_cast<double>(duration.count()) / iterations;
        EXPECT_LT(average_time_ns, 1000.0); // 平均每次链式操作小于1微秒
        
        record_benchmark("ResultChaining", std::chrono::nanoseconds(duration.count() / iterations));
    }

    // ==================== 压力测试 ====================

    TEST_F(TaskTest, ConcurrentTaskExecution) {
        const size_t num_tasks = 1000;
        std::vector<Task<int>> tasks;
        tasks.reserve(num_tasks);
        
        // 创建大量并发任务
        for (size_t i = 0; i < num_tasks; ++i) {
            tasks.emplace_back([i]() -> Task<int> {
                co_await sleep_for(std::chrono::milliseconds(1));
                co_return static_cast<int>(i);
            }());
        }
        
        // 等待所有任务完成
        std::vector<int> results;
        results.reserve(num_tasks);
        
        for (auto& task : tasks) {
            results.push_back(task.get());
        }
        
        // 验证结果
        EXPECT_EQ(results.size(), num_tasks);
        for (size_t i = 0; i < num_tasks; ++i) {
            EXPECT_EQ(results[i], static_cast<int>(i));
        }
    }

    // ==================== 边界条件测试 ====================

    TEST_F(TaskTest, TaskWithLargeData) {
        const size_t large_size = 1024 * 1024; // 1MB
        
        auto task = [large_size]() -> Task<std::vector<uint8_t>> {
            std::vector<uint8_t> large_data(large_size, 0x42);
            co_return large_data;
        }();
        
        auto result = task.get();
        EXPECT_EQ(result.size(), large_size);
        EXPECT_EQ(result[0], 0x42);
        EXPECT_EQ(result[large_size - 1], 0x42);
    }

    TEST_F(ResultTest, ResultWithComplexType) {
        struct ComplexType {
            std::string name;
            std::vector<int> values;
            std::unordered_map<std::string, double> properties;
        };
        
        ComplexType complex_data{
            "test",
            {1, 2, 3, 4, 5},
            {{"pi", 3.14159}, {"e", 2.71828}}
        };
        
        auto result = Result<ComplexType>::success(std::move(complex_data));
        
        EXPECT_TRUE(result.is_success());
        EXPECT_EQ(result.value().name, "test");
        EXPECT_EQ(result.value().values.size(), 5);
        EXPECT_EQ(result.value().properties.size(), 2);
        EXPECT_DOUBLE_EQ(result.value().properties.at("pi"), 3.14159);
    }

} // anonymous namespace

// ==================== 自定义测试主函数 ====================

int main(int argc, char** argv) {
    ::testing::InitGoogleTest(&argc, argv);
    
    // 注册测试环境
    ::testing::AddGlobalTestEnvironment(&TestEnvironment::instance());
    
    // 配置测试环境
    TestEnvironment::instance().enable_performance_tracking(true);
    TestEnvironment::instance().enable_memory_tracking(true);
    
    return RUN_ALL_TESTS();
}