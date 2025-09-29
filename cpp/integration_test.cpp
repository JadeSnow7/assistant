#include "include/nex/testing/test_framework.hpp"
#include "include/nex/core/async_types.hpp"
#include "include/nex/core/memory_manager.hpp"
#include "include/nex/core/scheduler.hpp"
#include "include/nex/platform/platform_factory_v2.hpp"
#include "include/nex/plugin/plugin_system.hpp"

#ifdef HUSHELL_ENABLE_GRPC
#include "include/nex/core/grpc_service.hpp"
#endif

using namespace hushell::testing;
using namespace hushell::core;

namespace {

    /**
     * @brief 集成测试基类
     */
    class IntegrationTestBase : public TestBase {
    protected:
        void SetUp() override {
            TestBase::SetUp();
            
            // 初始化内存管理器
            auto memory_result = memory::MemoryManager::instance().initialize();
            ASSERT_TRUE(memory_result.is_success()) << "Failed to initialize memory manager";
            
            // 初始化调度器
            auto scheduler_result = scheduler::SchedulerManager::instance().initialize();
            ASSERT_TRUE(scheduler_result.is_success()) << "Failed to initialize scheduler";
            
            // 初始化插件管理器
            auto plugin_result = plugin::PluginManager::instance().initialize();
            ASSERT_TRUE(plugin_result.is_success()) << "Failed to initialize plugin manager";
        }

        void TearDown() override {
            // 清理资源
            plugin::PluginManager::instance().shutdown();
            scheduler::SchedulerManager::instance().shutdown_all();
            memory::MemoryManager::instance().shutdown();
            
            TestBase::TearDown();
        }
    };

    // ==================== 系统初始化集成测试 ====================

    TEST_F(IntegrationTestBase, SystemInitialization) {
        // 验证所有核心组件都已正确初始化
        
        // 内存管理器
        auto& memory_manager = memory::MemoryManager::instance();
        EXPECT_TRUE(memory_manager.is_memory_healthy());
        
        // 调度器
        auto& scheduler = scheduler::SchedulerManager::instance().get_default_scheduler();
        auto load_info = scheduler.get_scheduler_stats();
        EXPECT_GT(load_info.total_threads, 0);
        
        // 插件管理器
        auto& plugin_manager = plugin::PluginManager::instance();
        auto plugin_stats = plugin_manager.get_stats();
        EXPECT_GE(plugin_stats.registered_loaders, 1); // 至少有默认加载器
        
        // 平台适配器
        auto& platform_factory = nex::platform::PlatformFactory::instance();
        auto platform_info = platform_factory.get_platform_info();
        EXPECT_NE(platform_info.type, nex::platform::PlatformType::UNKNOWN);
    }

    // ==================== 异步系统集成测试 ====================

    ASYNC_TEST(IntegrationTestBase, AsyncSystemIntegration) {
        auto& scheduler = scheduler::SchedulerManager::instance().get_default_scheduler();
        
        // 测试异步任务调度
        auto task1 = scheduler.schedule([]() -> int {
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
            return 42;
        });
        
        auto task2 = scheduler.schedule([]() -> std::string {
            std::this_thread::sleep_for(std::chrono::milliseconds(20));
            return "Hello World";
        });
        
        auto task3 = scheduler.schedule([]() -> double {
            std::this_thread::sleep_for(std::chrono::milliseconds(15));
            return 3.14159;
        });
        
        // 等待所有任务完成
        auto result1 = co_await task1;
        auto result2 = co_await task2;
        auto result3 = co_await task3;
        
        EXPECT_EQ(result1, 42);
        EXPECT_EQ(result2, "Hello World");
        EXPECT_DOUBLE_EQ(result3, 3.14159);
    }

    // ==================== 内存管理集成测试 ====================

    TEST_F(IntegrationTestBase, MemoryManagementIntegration) {
        auto& memory_manager = memory::MemoryManager::instance();
        
        // 测试对象池
        auto& int_pool = memory_manager.get_object_pool<int>();
        
        // 获取和释放对象
        std::vector<std::unique_ptr<int>> objects;
        for (int i = 0; i < 100; ++i) {
            auto obj = int_pool.acquire();
            *obj = i;
            objects.push_back(std::move(obj));
        }
        
        // 验证对象内容
        for (int i = 0; i < 100; ++i) {
            EXPECT_EQ(*objects[i], i);
        }
        
        // 释放对象
        for (auto& obj : objects) {
            int_pool.release(std::move(obj));
        }
        
        // 检查池统计
        auto pool_stats = int_pool.get_stats();
        EXPECT_EQ(pool_stats.allocated_count, 100);
        EXPECT_EQ(pool_stats.released_count, 100);
        
        // 测试高性能分配器
        auto& allocator = memory_manager.get_allocator();
        
        void* ptr1 = allocator.allocate(1024);
        void* ptr2 = allocator.allocate(2048);
        void* ptr3 = allocator.allocate(512);
        
        EXPECT_NE(ptr1, nullptr);
        EXPECT_NE(ptr2, nullptr);
        EXPECT_NE(ptr3, nullptr);
        
        // 写入数据验证
        memset(ptr1, 0x42, 1024);
        memset(ptr2, 0x55, 2048);
        memset(ptr3, 0x33, 512);
        
        EXPECT_EQ(static_cast<uint8_t*>(ptr1)[0], 0x42);
        EXPECT_EQ(static_cast<uint8_t*>(ptr2)[0], 0x55);
        EXPECT_EQ(static_cast<uint8_t*>(ptr3)[0], 0x33);
        
        allocator.deallocate(ptr1, 1024);
        allocator.deallocate(ptr2, 2048);
        allocator.deallocate(ptr3, 512);
        
        // 验证内存统计
        auto stats = allocator.get_stats();
        EXPECT_GT(stats.allocation_count, 0);
        EXPECT_GT(stats.deallocation_count, 0);
    }

    // ==================== 平台适配器集成测试 ====================

    TEST_F(IntegrationTestBase, PlatformAdapterIntegration) {
        auto adapter = nex::platform::PlatformFactory::instance().create_adapter();
        ASSERT_NE(adapter, nullptr);
        
        // 测试系统信息获取
        auto system_info = adapter->get_system_info();
        EXPECT_FALSE(system_info.hostname.empty());
        EXPECT_GT(system_info.cpu_cores, 0);
        EXPECT_GT(system_info.memory_total_gb, 0.0);
        
        // 测试进程管理
        auto processes = adapter->get_processes();
        EXPECT_FALSE(processes.empty());
        
        // 测试网络接口
        auto interfaces = adapter->get_network_interfaces();
        EXPECT_FALSE(interfaces.empty());
        
        // 测试环境变量
        auto path_env = adapter->get_environment_variable("PATH");
        EXPECT_TRUE(path_env.has_value());
        EXPECT_FALSE(path_env->empty());
    }

    // ==================== 插件系统集成测试 ====================

    TEST_F(IntegrationTestBase, PluginSystemIntegration) {
        auto& plugin_manager = plugin::PluginManager::instance();
        
        // 验证插件加载器已注册
        auto loader_names = plugin_manager.get_loader_names();
        EXPECT_FALSE(loader_names.empty());
        
        // 测试插件扫描（模拟）
        auto temp_dir = create_temp_directory();
        auto found_plugins = plugin_manager.scan_plugins(temp_dir);
        // 空目录应该返回空列表
        EXPECT_TRUE(found_plugins.empty());
        
        // 获取插件统计
        auto stats = plugin_manager.get_stats();
        EXPECT_EQ(stats.total_plugins, 0); // 没有加载插件
        EXPECT_GT(stats.registered_loaders, 0); // 但有注册的加载器
    }

    #ifdef HUSHELL_ENABLE_GRPC
    // ==================== gRPC服务集成测试 ====================

    ASYNC_TEST(IntegrationTestBase, GrpcServiceIntegration) {
        using namespace hushell::core::grpc;
        
        // 创建gRPC服务器配置
        GrpcServerConfig server_config;
        server_config.port = 0; // 使用系统分配的端口
        server_config.max_concurrent_streams = 100;
        
        // 创建服务器
        auto server = std::make_unique<GrpcServer>(server_config);
        
        // 启动服务器
        auto start_result = co_await server->start_async();
        EXPECT_TRUE(start_result.is_success()) << "Failed to start gRPC server: " << start_result.error_message();
        
        if (start_result.is_success()) {
            // 验证服务器状态
            EXPECT_TRUE(server->is_running());
            
            // 创建客户端配置
            GrpcClientConfig client_config;
            client_config.server_address = server->get_server_address();
            
            // 创建客户端
            auto client = std::make_unique<GrpcClient>(client_config);
            
            // 连接到服务器
            auto connect_result = co_await client->connect_async();
            EXPECT_TRUE(connect_result.is_success()) << "Failed to connect to gRPC server";
            
            if (connect_result.is_success()) {
                EXPECT_TRUE(client->is_connected());
                
                // 断开连接
                client->disconnect();
                EXPECT_FALSE(client->is_connected());
            }
            
            // 停止服务器
            auto stop_result = co_await server->stop_async();
            EXPECT_TRUE(stop_result.is_success()) << "Failed to stop gRPC server";
            
            EXPECT_FALSE(server->is_running());
        }
    }
    #endif

    // ==================== 性能集成测试 ====================

    PERFORMANCE_TEST(IntegrationTestBase, SystemPerformanceIntegration) {
        const size_t iterations = 1000;
        
        // 测试内存分配性能
        auto& allocator = memory::MemoryManager::instance().get_allocator();
        
        auto memory_test_time = measure_execution_time([&allocator, iterations]() {
            std::vector<void*> ptrs;
            ptrs.reserve(iterations);
            
            // 分配
            for (size_t i = 0; i < iterations; ++i) {
                void* ptr = allocator.allocate(1024 + i);
                ptrs.push_back(ptr);
            }
            
            // 释放
            for (size_t i = 0; i < iterations; ++i) {
                allocator.deallocate(ptrs[i], 1024 + i);
            }
        });
        
        // 1000次分配/释放应该在合理时间内完成
        EXPECT_LT(memory_test_time, std::chrono::milliseconds(100));
        
        record_benchmark("MemoryAllocDealloc", memory_test_time / iterations);
        
        // 测试异步任务调度性能
        auto& scheduler = scheduler::SchedulerManager::instance().get_default_scheduler();
        
        auto scheduling_test_time = measure_execution_time([&scheduler, iterations]() {
            std::vector<Task<int>> tasks;
            tasks.reserve(iterations);
            
            // 创建任务
            for (size_t i = 0; i < iterations; ++i) {
                tasks.emplace_back(scheduler.schedule([i]() -> int {
                    return static_cast<int>(i);
                }));
            }
            
            // 等待完成
            for (auto& task : tasks) {
                task.get();
            }
        });
        
        // 1000个简单任务应该在合理时间内完成
        EXPECT_LT(scheduling_test_time, std::chrono::seconds(1));
        
        record_benchmark("TaskScheduling", scheduling_test_time / iterations);
    }

    // ==================== 压力集成测试 ====================

    TEST_F(IntegrationTestBase, SystemStressIntegration) {
        const size_t thread_count = 20;
        const size_t iterations_per_thread = 100;
        
        run_concurrent_test([this](size_t thread_id) {
            auto& memory_manager = memory::MemoryManager::instance();
            auto& scheduler = scheduler::SchedulerManager::instance().get_default_scheduler();
            
            for (size_t i = 0; i < iterations_per_thread; ++i) {
                // 内存操作
                auto& allocator = memory_manager.get_allocator();
                void* ptr = allocator.allocate(1024);
                EXPECT_NE(ptr, nullptr);
                
                // 写入数据
                memset(ptr, static_cast<int>(thread_id + i), 1024);
                
                // 异步任务
                auto task = scheduler.schedule([thread_id, i]() -> size_t {
                    return thread_id * 1000 + i;
                });
                
                auto result = task.get();
                EXPECT_EQ(result, thread_id * 1000 + i);
                
                // 释放内存
                allocator.deallocate(ptr, 1024);
            }
        }, thread_count);
        
        // 验证系统仍然健康
        EXPECT_TRUE(memory::MemoryManager::instance().is_memory_healthy());
        
        auto scheduler_stats = scheduler::SchedulerManager::instance().get_default_scheduler().get_scheduler_stats();
        EXPECT_GT(scheduler_stats.total_threads, 0);
    }

    // ==================== 错误处理集成测试 ====================

    TEST_F(IntegrationTestBase, ErrorHandlingIntegration) {
        // 测试内存分配失败处理
        auto& allocator = memory::MemoryManager::instance().get_allocator();
        
        // 尝试分配一个非常大的内存块（应该失败）
        void* large_ptr = allocator.allocate(SIZE_MAX / 2);
        if (large_ptr == nullptr) {
            // 这是预期的行为
            SUCCEED();
        } else {
            // 如果分配成功（不太可能），需要释放
            allocator.deallocate(large_ptr, SIZE_MAX / 2);
            FAIL() << "Unexpectedly succeeded in allocating huge memory block";
        }
        
        // 测试异步任务异常处理
        auto& scheduler = scheduler::SchedulerManager::instance().get_default_scheduler();
        
        auto failing_task = scheduler.schedule([]() -> int {
            throw std::runtime_error("Test exception");
            return 42;
        });
        
        EXPECT_THROW(failing_task.get(), std::runtime_error);
    }

    // ==================== 资源清理验证 ====================

    TEST_F(IntegrationTestBase, ResourceCleanupVerification) {
        // 记录初始资源状态
        auto initial_memory_stats = memory::MemoryManager::instance().get_global_stats();
        
        {
            // 在作用域内分配大量资源
            auto& allocator = memory::MemoryManager::instance().get_allocator();
            auto& scheduler = scheduler::SchedulerManager::instance().get_default_scheduler();
            
            std::vector<void*> allocated_ptrs;
            std::vector<Task<int>> tasks;
            
            // 分配内存
            for (int i = 0; i < 100; ++i) {
                void* ptr = allocator.allocate(1024);
                if (ptr) {
                    allocated_ptrs.push_back(ptr);
                }
            }
            
            // 创建任务
            for (int i = 0; i < 50; ++i) {
                tasks.emplace_back(scheduler.schedule([i]() -> int {
                    std::this_thread::sleep_for(std::chrono::milliseconds(1));
                    return i;
                }));
            }
            
            // 等待任务完成
            for (auto& task : tasks) {
                task.get();
            }
            
            // 释放内存
            for (size_t i = 0; i < allocated_ptrs.size(); ++i) {
                allocator.deallocate(allocated_ptrs[i], 1024);
            }
        }
        
        // 强制清理
        memory::MemoryManager::instance().force_gc();
        
        // 检查资源是否正确清理
        auto final_memory_stats = memory::MemoryManager::instance().get_global_stats();
        
        // 分配和释放应该是平衡的
        EXPECT_GE(final_memory_stats.deallocation_count, final_memory_stats.allocation_count - initial_memory_stats.allocation_count);
    }

} // anonymous namespace

// ==================== 集成测试主函数 ====================

int main(int argc, char** argv) {
    ::testing::InitGoogleTest(&argc, argv);
    
    // 注册测试环境
    ::testing::AddGlobalTestEnvironment(&TestEnvironment::instance());
    
    // 配置测试环境
    TestEnvironment::instance().enable_performance_tracking(true);
    TestEnvironment::instance().enable_memory_tracking(true);
    TestEnvironment::instance().set_global_config("test_mode", "integration");
    
    std::cout << "=== hushell C++重构集成测试 ===" << std::endl;
    std::cout << "平台: " << nex::platform::utils::get_platform_summary() << std::endl;
    std::cout << "兼容性: " << (nex::platform::utils::is_platform_compatible() ? "✓" : "✗") << std::endl;
    std::cout << "================================" << std::endl;
    
    auto result = RUN_ALL_TESTS();
    
    std::cout << "=== 集成测试完成 ===" << std::endl;
    
    return result;
}