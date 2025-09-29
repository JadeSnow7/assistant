#include "../../include/nex/testing/test_framework.hpp"
#include "../../include/nex/platform/platform_factory_v2.hpp"
#include "../../include/nex/platform/platform_adapter.hpp"

using namespace hushell::testing;
using namespace nex::platform;

namespace {

    /**
     * @brief 平台适配器测试基类
     */
    class PlatformAdapterTest : public TestBase {
    protected:
        void SetUp() override {
            TestBase::SetUp();
            adapter_ = PlatformFactory::instance().create_adapter();
            ASSERT_NE(adapter_, nullptr) << "Failed to create platform adapter";
        }

        void TearDown() override {
            adapter_.reset();
            TestBase::TearDown();
        }

        std::unique_ptr<IPlatformAdapter> adapter_;
    };

    /**
     * @brief 平台工厂测试类
     */
    class PlatformFactoryTest : public TestBase {
    protected:
        void SetUp() override {
            TestBase::SetUp();
        }
    };

    // ==================== 平台检测测试 ====================

    TEST_F(PlatformFactoryTest, PlatformDetection) {
        auto& factory = PlatformFactory::instance();
        auto platform_type = factory.detect_platform();
        
        EXPECT_NE(platform_type, PlatformType::UNKNOWN);
        
        // 验证检测到的平台与编译时平台匹配
        #ifdef HUSHELL_PLATFORM_LINUX
        EXPECT_EQ(platform_type, PlatformType::LINUX);
        #elif defined(HUSHELL_PLATFORM_WINDOWS)
        EXPECT_EQ(platform_type, PlatformType::WINDOWS);
        #elif defined(HUSHELL_PLATFORM_MACOS)
        EXPECT_EQ(platform_type, PlatformType::MACOS);
        #endif
    }

    TEST_F(PlatformFactoryTest, PlatformInfo) {
        auto& factory = PlatformFactory::instance();
        auto platform_info = factory.get_platform_info();
        
        EXPECT_FALSE(platform_info.name.empty());
        EXPECT_FALSE(platform_info.version.empty());
        EXPECT_FALSE(platform_info.architecture.empty());
        EXPECT_GT(platform_info.cpu_cores, 0);
        EXPECT_GT(platform_info.memory_gb, 0);
    }

    TEST_F(PlatformFactoryTest, FeatureSupport) {
        auto& factory = PlatformFactory::instance();
        
        // 所有平台都应该支持的基础特性
        EXPECT_TRUE(factory.supports_feature(PlatformFeatures::MULTI_THREADING));
        EXPECT_TRUE(factory.supports_feature(PlatformFeatures::MEMORY_MAPPING));
        EXPECT_TRUE(factory.supports_feature(PlatformFeatures::NETWORK_SUPPORT));
        
        // 平台特定特性测试
        #ifdef HUSHELL_PLATFORM_LINUX
        EXPECT_TRUE(factory.supports_feature(PlatformFeatures::EPOLL_SUPPORT));
        #endif
        
        #ifdef HUSHELL_PLATFORM_WINDOWS
        EXPECT_TRUE(factory.supports_feature(PlatformFeatures::IOCP_SUPPORT));
        #endif
        
        #ifdef HUSHELL_PLATFORM_MACOS
        EXPECT_TRUE(factory.supports_feature(PlatformFeatures::GCD_SUPPORT));
        #endif
    }

    TEST_F(PlatformFactoryTest, CompatibilityCheck) {
        auto& factory = PlatformFactory::instance();
        auto compatibility = factory.check_compatibility();
        
        EXPECT_TRUE(compatibility.is_supported) << "Platform should be supported";
        EXPECT_FALSE(compatibility.minimum_version.empty());
    }

    // ==================== 系统信息测试 ====================

    TEST_F(PlatformAdapterTest, SystemInfo) {
        auto system_info = adapter_->get_system_info();
        
        // 基础字段验证
        EXPECT_FALSE(system_info.hostname.empty());
        EXPECT_FALSE(system_info.os_name.empty());
        EXPECT_FALSE(system_info.architecture.empty());
        
        // 数值字段验证
        EXPECT_GT(system_info.cpu_cores, 0);
        EXPECT_GT(system_info.cpu_threads, 0);
        EXPECT_GE(system_info.cpu_usage, 0.0);
        EXPECT_LE(system_info.cpu_usage, 100.0);
        
        EXPECT_GT(system_info.memory_total_gb, 0.0);
        EXPECT_GE(system_info.memory_available_gb, 0.0);
        EXPECT_LE(system_info.memory_available_gb, system_info.memory_total_gb);
        EXPECT_GE(system_info.memory_usage, 0.0);
        EXPECT_LE(system_info.memory_usage, 100.0);
        
        EXPECT_GT(system_info.disk_total_gb, 0.0);
        EXPECT_GE(system_info.disk_available_gb, 0.0);
        EXPECT_LE(system_info.disk_available_gb, system_info.disk_total_gb);
        
        EXPECT_GE(system_info.uptime.count(), 0);
    }

    // ==================== 进程管理测试 ====================

    TEST_F(PlatformAdapterTest, GetProcesses) {
        auto processes = adapter_->get_processes();
        
        EXPECT_FALSE(processes.empty()) << "Should find at least current process";
        
        // 验证进程信息的有效性
        bool found_current_process = false;
        auto current_pid = 
        #ifdef HUSHELL_PLATFORM_WINDOWS
            GetCurrentProcessId();
        #else
            getpid();
        #endif
        
        for (const auto& process : processes) {
            EXPECT_GT(process.pid, 0);
            EXPECT_FALSE(process.name.empty());
            
            if (process.pid == current_pid) {
                found_current_process = true;
            }
        }
        
        EXPECT_TRUE(found_current_process) << "Should find current process in process list";
    }

    TEST_F(PlatformAdapterTest, GetProcessByPid) {
        auto current_pid = 
        #ifdef HUSHELL_PLATFORM_WINDOWS
            GetCurrentProcessId();
        #else
            getpid();
        #endif
        
        auto process_info = adapter_->get_process_by_pid(current_pid);
        
        ASSERT_TRUE(process_info.has_value()) << "Should find current process";
        EXPECT_EQ(process_info->pid, current_pid);
        EXPECT_FALSE(process_info->name.empty());
    }

    TEST_F(PlatformAdapterTest, FindProcessesByName) {
        // 使用当前进程名进行搜索
        auto current_pid = 
        #ifdef HUSHELL_PLATFORM_WINDOWS
            GetCurrentProcessId();
        #else
            getpid();
        #endif
        
        auto current_process = adapter_->get_process_by_pid(current_pid);
        ASSERT_TRUE(current_process.has_value());
        
        auto processes = adapter_->find_processes_by_name(current_process->name);
        EXPECT_FALSE(processes.empty());
        
        // 应该至少找到当前进程
        bool found_current = false;
        for (const auto& process : processes) {
            if (process.pid == current_pid) {
                found_current = true;
                break;
            }
        }
        EXPECT_TRUE(found_current);
    }

    // ==================== 文件系统测试 ====================

    TEST_F(PlatformAdapterTest, DirectoryOperations) {
        auto temp_dir = adapter_->get_temp_directory();
        auto home_dir = adapter_->get_home_directory();
        auto config_dir = adapter_->get_config_directory();
        
        EXPECT_TRUE(std::filesystem::exists(temp_dir));
        EXPECT_TRUE(std::filesystem::exists(home_dir));
        
        // 配置目录可能不存在，但路径应该有效
        EXPECT_FALSE(config_dir.empty());
    }

    TEST_F(PlatformAdapterTest, FilePermissions) {
        auto temp_file = create_temp_file("test content");
        
        EXPECT_TRUE(std::filesystem::exists(temp_file));
        
        // 测试权限设置（Unix系统）
        #ifndef HUSHELL_PLATFORM_WINDOWS
        bool result = adapter_->set_file_permissions(temp_file, 0644);
        EXPECT_TRUE(result);
        #endif
    }

    TEST_F(PlatformAdapterTest, ExecutableCheck) {
        // 创建一个可执行文件
        auto temp_file = create_temp_file("#!/bin/bash\necho 'test'\n");
        
        #ifndef HUSHELL_PLATFORM_WINDOWS
        adapter_->set_file_permissions(temp_file, 0755);
        EXPECT_TRUE(adapter_->is_executable(temp_file));
        #endif
    }

    // ==================== 网络功能测试 ====================

    TEST_F(PlatformAdapterTest, NetworkInterfaces) {
        auto interfaces = adapter_->get_network_interfaces();
        
        EXPECT_FALSE(interfaces.empty()) << "Should have at least loopback interface";
        
        bool found_loopback = false;
        for (const auto& interface : interfaces) {
            EXPECT_FALSE(interface.name.empty());
            
            if (interface.is_loopback) {
                found_loopback = true;
                EXPECT_THAT(interface.ip_address, ::testing::AnyOf("127.0.0.1", "::1"));
            }
        }
        
        EXPECT_TRUE(found_loopback) << "Should find loopback interface";
    }

    TEST_F(PlatformAdapterTest, LocalIPAddresses) {
        auto ip_addresses = adapter_->get_local_ip_addresses();
        
        EXPECT_FALSE(ip_addresses.empty()) << "Should have at least loopback IP";
        
        bool found_loopback = false;
        for (const auto& ip : ip_addresses) {
            EXPECT_FALSE(ip.empty());
            if (ip == "127.0.0.1" || ip == "::1") {
                found_loopback = true;
            }
        }
        
        EXPECT_TRUE(found_loopback) << "Should find loopback IP address";
    }

    TEST_F(PlatformAdapterTest, PortAvailability) {
        // 测试一些常见端口
        
        // 端口0应该总是可用（系统会分配一个可用端口）
        EXPECT_TRUE(adapter_->is_port_available(0));
        
        // 测试一些不太可能被占用的高端口
        EXPECT_TRUE(adapter_->is_port_available(65432));
        EXPECT_TRUE(adapter_->is_port_available(65433));
    }

    // ==================== 硬件信息测试 ====================

    TEST_F(PlatformAdapterTest, HardwareDetection) {
        // CUDA可用性检测
        bool cuda_available = adapter_->is_cuda_available();
        // 不强制要求CUDA可用，只验证函数正常执行
        
        // OpenCL可用性检测
        bool opencl_available = adapter_->is_opencl_available();
        // 不强制要求OpenCL可用，只验证函数正常执行
        
        // 记录检测结果
        if (cuda_available) {
            _log_info("CUDA support detected");
        }
        if (opencl_available) {
            _log_info("OpenCL support detected");
        }
    }

    TEST_F(PlatformAdapterTest, GPUInfo) {
        auto gpu_info = adapter_->get_gpu_info();
        
        // GPU信息可能为空（在没有独立GPU的系统上）
        for (const auto& gpu : gpu_info) {
            EXPECT_FALSE(gpu.name.empty());
            EXPECT_FALSE(gpu.vendor.empty());
            
            if (gpu.memory_total_mb > 0) {
                EXPECT_LE(gpu.memory_used_mb, gpu.memory_total_mb);
            }
            
            EXPECT_GE(gpu.utilization, 0.0);
            EXPECT_LE(gpu.utilization, 100.0);
        }
    }

    // ==================== 环境变量测试 ====================

    TEST_F(PlatformAdapterTest, EnvironmentVariables) {
        const std::string test_var_name = "HUSHELL_TEST_VAR";
        const std::string test_var_value = "test_value_123";
        
        // 设置环境变量
        bool set_result = adapter_->set_environment_variable(test_var_name, test_var_value);
        EXPECT_TRUE(set_result);
        
        // 读取环境变量
        auto retrieved_value = adapter_->get_environment_variable(test_var_name);
        ASSERT_TRUE(retrieved_value.has_value());
        EXPECT_EQ(retrieved_value.value(), test_var_value);
        
        // 清理测试环境变量
        #ifdef HUSHELL_PLATFORM_WINDOWS
        adapter_->set_environment_variable(test_var_name, "");
        #else
        unsetenv(test_var_name.c_str());
        #endif
    }

    // ==================== 性能测试 ====================

    PERFORMANCE_TEST(PlatformAdapterTest, SystemInfoPerformance) {
        const size_t iterations = 100;
        
        ASSERT_EXECUTION_TIME_LESS_THAN([this, iterations]() {
            for (size_t i = 0; i < iterations; ++i) {
                auto system_info = adapter_->get_system_info();
                (void)system_info; // 防止优化
            }
        }, std::chrono::milliseconds(1000)); // 100次调用应在1秒内完成
    }

    PERFORMANCE_TEST(PlatformAdapterTest, ProcessListPerformance) {
        ASSERT_EXECUTION_TIME_LESS_THAN([this]() {
            auto processes = adapter_->get_processes();
            EXPECT_FALSE(processes.empty());
        }, std::chrono::milliseconds(5000)); // 获取进程列表应在5秒内完成
    }

    // ==================== 压力测试 ====================

    TEST_F(PlatformAdapterTest, ConcurrentSystemInfoAccess) {
        const size_t thread_count = 10;
        const size_t iterations_per_thread = 50;
        
        run_concurrent_test([this](size_t thread_id) {
            for (size_t i = 0; i < iterations_per_thread; ++i) {
                auto system_info = adapter_->get_system_info();
                EXPECT_GT(system_info.cpu_cores, 0);
                EXPECT_GT(system_info.memory_total_gb, 0.0);
            }
        }, thread_count);
    }

    // ==================== 平台特定测试 ====================

    #ifdef HUSHELL_PLATFORM_LINUX
    TEST_F(PlatformAdapterTest, LinuxSpecificFeatures) {
        // 测试Linux特定功能
        auto cpu_temp = adapter_->get_cpu_temperature();
        if (cpu_temp.has_value()) {
            EXPECT_GT(cpu_temp.value(), 0.0);
            EXPECT_LT(cpu_temp.value(), 150.0); // 合理的CPU温度范围
        }
    }
    #endif

    #ifdef HUSHELL_PLATFORM_WINDOWS
    TEST_F(PlatformAdapterTest, WindowsSpecificFeatures) {
        // 测试Windows特定功能
        // 可以添加Windows特定的测试
    }
    #endif

    #ifdef HUSHELL_PLATFORM_MACOS
    TEST_F(PlatformAdapterTest, MacOSSpecificFeatures) {
        // 测试macOS特定功能
        // 可以添加macOS特定的测试
    }
    #endif

} // anonymous namespace