#pragma once

#include "platform_adapter.hpp"
#include "linux_platform_adapter.hpp"
#include "windows_platform_adapter.hpp"
#include "macos_platform_adapter.hpp"
#include "../platform_config.h"
#include <memory>
#include <unordered_map>
#include <string>

namespace nex::platform {

    /**
     * @brief 平台类型枚举
     */
    enum class PlatformType {
        UNKNOWN = 0,
        LINUX = 1,
        WINDOWS = 2,
        MACOS = 3
    };

    /**
     * @brief 平台特性标志
     */
    enum class PlatformFeatures : uint32_t {
        NONE = 0x00000000,
        
        // 通用特性
        MULTI_THREADING = 0x00000001,
        MEMORY_MAPPING = 0x00000002,
        NETWORK_SUPPORT = 0x00000004,
        GPU_COMPUTE = 0x00000008,
        
        // Linux特性
        EPOLL_SUPPORT = 0x00000010,
        NUMA_SUPPORT = 0x00000020,
        SYSTEMD_SUPPORT = 0x00000040,
        PERF_EVENTS = 0x00000080,
        
        // Windows特性
        IOCP_SUPPORT = 0x00000100,
        ETW_SUPPORT = 0x00000200,
        DIRECTML_SUPPORT = 0x00000400,
        WMI_SUPPORT = 0x00000800,
        
        // macOS特性
        GCD_SUPPORT = 0x00001000,
        METAL_SUPPORT = 0x00002000,
        COREML_SUPPORT = 0x00004000,
        INSTRUMENTS_SUPPORT = 0x00008000,
        
        // 高级特性
        CONTAINER_SUPPORT = 0x00010000,
        VIRTUALIZATION = 0x00020000,
        SECURE_BOOT = 0x00040000,
        TPM_SUPPORT = 0x00080000
    };

    // 位运算操作符重载
    inline PlatformFeatures operator|(PlatformFeatures lhs, PlatformFeatures rhs) {
        return static_cast<PlatformFeatures>(
            static_cast<uint32_t>(lhs) | static_cast<uint32_t>(rhs)
        );
    }

    inline PlatformFeatures operator&(PlatformFeatures lhs, PlatformFeatures rhs) {
        return static_cast<PlatformFeatures>(
            static_cast<uint32_t>(lhs) & static_cast<uint32_t>(rhs)
        );
    }

    inline bool has_feature(PlatformFeatures features, PlatformFeatures feature) {
        return (features & feature) == feature;
    }

    /**
     * @brief 平台信息结构体
     */
    struct PlatformInfo {
        PlatformType type = PlatformType::UNKNOWN;
        std::string name;
        std::string version;
        std::string architecture;
        PlatformFeatures features = PlatformFeatures::NONE;
        
        // 性能特征
        int cpu_cores = 0;
        size_t memory_gb = 0;
        bool has_gpu = false;
        bool has_nvme = false;
        
        // 容器/虚拟化信息
        bool is_containerized = false;
        bool is_virtualized = false;
        std::string container_type;
        std::string hypervisor_type;
    };

    /**
     * @brief 平台工厂类 - 创建和管理平台适配器
     */
    class PlatformFactory {
    public:
        /**
         * @brief 获取单例实例
         */
        static PlatformFactory& instance();

        /**
         * @brief 检测当前平台
         */
        PlatformType detect_platform() const;

        /**
         * @brief 获取平台信息
         */
        PlatformInfo get_platform_info() const;

        /**
         * @brief 检查平台特性支持
         */
        bool supports_feature(PlatformFeatures feature) const;

        /**
         * @brief 创建平台适配器
         */
        std::unique_ptr<IPlatformAdapter> create_adapter() const;

        /**
         * @brief 创建指定平台的适配器
         */
        std::unique_ptr<IPlatformAdapter> create_adapter(PlatformType platform) const;

        /**
         * @brief 创建优化的平台适配器
         */
        std::unique_ptr<IPlatformAdapter> create_optimized_adapter(
            const std::unordered_map<std::string, std::string>& config = {}
        ) const;

        /**
         * @brief 获取支持的平台列表
         */
        std::vector<PlatformType> get_supported_platforms() const;

        /**
         * @brief 获取平台名称
         */
        std::string get_platform_name(PlatformType platform) const;

        /**
         * @brief 注册自定义平台适配器工厂
         */
        using AdapterFactory = std::function<std::unique_ptr<IPlatformAdapter>()>;
        void register_adapter_factory(PlatformType platform, AdapterFactory factory);

        /**
         * @brief 平台兼容性检查
         */
        struct CompatibilityInfo {
            bool is_supported = false;
            std::string minimum_version;
            std::vector<std::string> required_features;
            std::vector<std::string> missing_features;
            std::vector<std::string> warnings;
        };
        CompatibilityInfo check_compatibility() const;

        /**
         * @brief 性能基准测试
         */
        struct BenchmarkResults {
            double cpu_score = 0.0;
            double memory_score = 0.0;
            double disk_score = 0.0;
            double network_score = 0.0;
            double overall_score = 0.0;
            std::chrono::milliseconds test_duration{0};
        };
        BenchmarkResults run_platform_benchmark() const;

        /**
         * @brief 推荐的平台配置
         */
        std::unordered_map<std::string, std::string> get_recommended_config() const;

    private:
        PlatformFactory() = default;
        ~PlatformFactory() = default;

        // 禁用拷贝和移动
        PlatformFactory(const PlatformFactory&) = delete;
        PlatformFactory& operator=(const PlatformFactory&) = delete;

        // 内部方法
        PlatformFeatures detect_platform_features() const;
        bool is_feature_available(PlatformFeatures feature) const;
        
        // 平台特定检测方法
        bool detect_linux_features() const;
        bool detect_windows_features() const;
        bool detect_macos_features() const;

        // 自定义适配器工厂
        std::unordered_map<PlatformType, AdapterFactory> custom_factories_;
        mutable std::mutex factories_mutex_;
    };

    /**
     * @brief 平台感知的资源管理器
     */
    class PlatformResourceManager {
    public:
        /**
         * @brief 构造函数
         */
        explicit PlatformResourceManager(std::unique_ptr<IPlatformAdapter> adapter);

        /**
         * @brief 析构函数
         */
        ~PlatformResourceManager();

        /**
         * @brief 优化系统资源配置
         */
        bool optimize_system_resources();

        /**
         * @brief 设置进程优先级
         */
        bool set_process_priority(int priority);

        /**
         * @brief 设置CPU亲和性
         */
        bool set_cpu_affinity(const std::vector<int>& cpu_list);

        /**
         * @brief 预分配内存
         */
        bool preallocate_memory(size_t size_mb);

        /**
         * @brief 配置网络优化
         */
        bool configure_network_optimization();

        /**
         * @brief 启用GPU加速
         */
        bool enable_gpu_acceleration();

        /**
         * @brief 监控资源使用情况
         */
        struct ResourceUsage {
            double cpu_usage = 0.0;
            double memory_usage = 0.0;
            double disk_usage = 0.0;
            double network_usage = 0.0;
            double gpu_usage = 0.0;
            std::chrono::steady_clock::time_point timestamp;
        };
        ResourceUsage get_resource_usage() const;

        /**
         * @brief 获取平台适配器
         */
        IPlatformAdapter& get_adapter() const;

    private:
        std::unique_ptr<IPlatformAdapter> adapter_;
        std::atomic<bool> optimized_{false};
    };

    /**
     * @brief 便利函数
     */
    namespace utils {
        
        /**
         * @brief 创建默认平台适配器
         */
        inline std::unique_ptr<IPlatformAdapter> create_default_adapter() {
            return PlatformFactory::instance().create_adapter();
        }

        /**
         * @brief 检查当前平台是否支持特定功能
         */
        inline bool is_feature_supported(PlatformFeatures feature) {
            return PlatformFactory::instance().supports_feature(feature);
        }

        /**
         * @brief 获取当前平台类型
         */
        inline PlatformType get_current_platform() {
            return PlatformFactory::instance().detect_platform();
        }

        /**
         * @brief 获取平台信息摘要
         */
        inline std::string get_platform_summary() {
            auto info = PlatformFactory::instance().get_platform_info();
            return info.name + " " + info.version + " (" + info.architecture + ")";
        }

        /**
         * @brief 运行平台兼容性检查
         */
        inline bool is_platform_compatible() {
            auto compat = PlatformFactory::instance().check_compatibility();
            return compat.is_supported;
        }

        /**
         * @brief 应用推荐的平台优化
         */
        bool apply_recommended_optimizations();

        /**
         * @brief 生成平台报告
         */
        std::string generate_platform_report();
    }

} // namespace nex::platform