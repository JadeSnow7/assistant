#pragma once

#include "platform_adapter.hpp"
#include "../platform_config.h"

#ifdef HUSHELL_PLATFORM_MACOS

#include <mach/mach.h>
#include <mach/mach_host.h>
#include <mach/host_info.h>
#include <mach/machine.h>
#include <sys/types.h>
#include <sys/sysctl.h>
#include <sys/mount.h>
#include <CoreFoundation/CoreFoundation.h>
#include <IOKit/IOKitLib.h>
#include <dispatch/dispatch.h>

#ifdef HUSHELL_HAS_METAL
#include <Metal/Metal.h>
#endif

#ifdef HUSHELL_HAS_COREML
#include <CoreML/CoreML.h>
#endif

namespace nex::platform::macos {

    /**
     * @brief macOS性能指标
     */
    struct MacOSPerfMetrics {
        double cpu_usage = 0.0;
        double memory_pressure = 0.0;
        double thermal_state = 0.0;
        uint64_t mach_calls = 0;
        uint64_t syscalls = 0;
        uint64_t interrupts = 0;
    };

    /**
     * @brief Grand Central Dispatch队列管理器
     */
    class GCDQueueManager {
    public:
        GCDQueueManager();
        ~GCDQueueManager();

        /**
         * @brief 设置GCD队列
         */
        void setup_gcd_queues();

        /**
         * @brief 获取全局并发队列
         */
        dispatch_queue_t get_global_queue(dispatch_qos_class_t qos_class);

        /**
         * @brief 创建自定义队列
         */
        dispatch_queue_t create_custom_queue(const std::string& label, 
                                           dispatch_queue_attr_t attributes);

        /**
         * @brief 异步执行任务
         */
        void async_execute(dispatch_queue_t queue, dispatch_block_t block);

        /**
         * @brief 同步执行任务
         */
        void sync_execute(dispatch_queue_t queue, dispatch_block_t block);

        /**
         * @brief 延迟执行任务
         */
        void delayed_execute(dispatch_queue_t queue, dispatch_time_t when, dispatch_block_t block);

    private:
        std::vector<dispatch_queue_t> custom_queues_;
    };

    /**
     * @brief Metal计算设备管理器
     */
    class MetalComputeManager {
    public:
        MetalComputeManager();
        ~MetalComputeManager();

        /**
         * @brief 设置Metal计算
         */
        bool setup_metal_compute();

        /**
         * @brief 获取Metal设备
         */
        id<MTLDevice> get_metal_device();

        /**
         * @brief 检查Metal可用性
         */
        bool is_metal_available() const;

        /**
         * @brief 获取Metal性能着色器支持
         */
        bool supports_metal_performance_shaders() const;

        /**
         * @brief 执行Metal计算任务
         */
        bool execute_compute_task(const std::string& shader_code, 
                                const std::vector<void*>& buffers);

    private:
        id<MTLDevice> metal_device_;
        id<MTLCommandQueue> command_queue_;
        bool metal_available_;
    };

    /**
     * @brief 电源管理器
     */
    class PowerManager {
    public:
        PowerManager();
        ~PowerManager();

        /**
         * @brief 设置电源管理
         */
        void setup_power_management();

        /**
         * @brief 获取电池状态
         */
        struct BatteryStatus {
            bool is_charging = false;
            double charge_level = 0.0;
            double time_remaining_minutes = 0.0;
            double temperature = 0.0;
            int cycle_count = 0;
        };
        BatteryStatus get_battery_status() const;

        /**
         * @brief 获取热力状态
         */
        enum class ThermalState {
            NOMINAL,
            FAIR,
            SERIOUS,
            CRITICAL
        };
        ThermalState get_thermal_state() const;

        /**
         * @brief 设置电源断言
         */
        bool create_power_assertion(const std::string& assertion_name);

        /**
         * @brief 释放电源断言
         */
        void release_power_assertion();

        /**
         * @brief 监听电源事件
         */
        void register_power_notifications(std::function<void(const std::string&)> callback);

    private:
        IOPMAssertionID assertion_id_;
        io_connect_t power_connection_;
        std::function<void(const std::string&)> notification_callback_;
    };

    /**
     * @brief macOS平台适配器实现
     */
    class MacOSPlatformAdapter : public IPlatformAdapter {
    public:
        MacOSPlatformAdapter();
        virtual ~MacOSPlatformAdapter();

        // ========== 生命周期管理 ==========
        bool initialize();
        void shutdown();

        // ========== 进程管理 ==========
        std::vector<ProcessInfo> get_processes() const override;
        std::optional<ProcessInfo> get_process_by_pid(int pid) const override;
        std::vector<ProcessInfo> find_processes_by_name(const std::string& name) const override;
        bool kill_process(int pid, int signal = SIGTERM) const override;
        std::optional<ProcessInfo> start_process(
            const std::string& command,
            const std::filesystem::path& working_dir = std::filesystem::current_path()
        ) const override;

        // ========== 系统信息 ==========
        SystemInfo get_system_info() const override;
        std::vector<GpuInfo> get_gpu_info() const override;
        std::optional<std::string> get_environment_variable(const std::string& name) const override;
        bool set_environment_variable(const std::string& name, const std::string& value) const override;

        // ========== 文件系统 ==========
        std::filesystem::path get_temp_directory() const override;
        std::filesystem::path get_home_directory() const override;
        std::filesystem::path get_config_directory() const override;
        std::filesystem::path get_library_directory() const override;
        bool is_executable(const std::filesystem::path& path) const override;
        bool set_file_permissions(const std::filesystem::path& path, int permissions) const override;

        // ========== 网络 ==========
        std::vector<NetworkInterface> get_network_interfaces() const override;
        bool is_port_available(int port, const std::string& protocol = "tcp") const override;
        std::vector<std::string> get_local_ip_addresses() const override;

        // ========== 硬件信息 ==========
        bool is_cuda_available() const override;
        bool is_opencl_available() const override;
        std::optional<double> get_cpu_temperature() const override;

        // ========== macOS特定功能 ==========

        /**
         * @brief 设置GCD队列
         */
        void setup_gcd_queues();

        /**
         * @brief 设置Metal计算
         */
        void setup_metal_compute();

        /**
         * @brief 设置Instruments性能分析
         */
        void setup_instruments_profiling();

        /**
         * @brief 设置电源管理
         */
        void setup_power_management();

        /**
         * @brief 获取macOS版本信息
         */
        struct MacOSVersionInfo {
            int major_version = 0;
            int minor_version = 0;
            int patch_version = 0;
            std::string version_string;
            std::string build_number;
            std::string product_name;
        };
        MacOSVersionInfo get_macos_version_info() const;

        /**
         * @brief 获取macOS性能指标
         */
        MacOSPerfMetrics get_macos_perf_metrics() const;

        /**
         * @brief 获取系统配置信息
         */
        template<typename T>
        std::optional<T> get_sysctl_value(const std::string& name) const;

        /**
         * @brief 设置系统配置
         */
        template<typename T>
        bool set_sysctl_value(const std::string& name, const T& value);

        /**
         * @brief 获取Mach主机信息
         */
        struct MachHostInfo {
            uint32_t cpu_count = 0;
            uint32_t cpu_type = 0;
            uint32_t cpu_subtype = 0;
            uint32_t memory_size_mb = 0;
            uint32_t max_cpus = 0;
            uint32_t max_mem = 0;
        };
        MachHostInfo get_mach_host_info() const;

        /**
         * @brief 获取IOKit设备信息
         */
        std::vector<std::unordered_map<std::string, std::string>> 
        get_iokit_devices(const std::string& service_type) const;

        /**
         * @brief 检查SIP（系统完整性保护）状态
         */
        bool is_sip_enabled() const;

        /**
         * @brief 检查代码签名状态
         */
        bool verify_code_signature(const std::filesystem::path& path) const;

        /**
         * @brief 获取安全策略信息
         */
        struct SecurityPolicy {
            bool sip_enabled = false;
            bool gatekeeper_enabled = false;
            bool xprotect_enabled = false;
            std::string quarantine_status;
        };
        SecurityPolicy get_security_policy() const;

        /**
         * @brief 启用性能优化
         */
        void optimize_for_platform() override;

        /**
         * @brief 检查是否在虚拟机中运行
         */
        bool is_running_in_vm() const;

        /**
         * @brief 获取虚拟机类型
         */
        std::string get_vm_type() const;

        /**
         * @brief 获取Apple芯片信息
         */
        struct AppleChipInfo {
            std::string chip_name;
            int performance_cores = 0;
            int efficiency_cores = 0;
            int gpu_cores = 0;
            int neural_engine_cores = 0;
            bool has_secure_enclave = false;
        };
        std::optional<AppleChipInfo> get_apple_chip_info() const;

    private:
        // 内部实现方法
        ProcessInfo create_process_info_from_pid(pid_t pid) const;
        std::string cfstring_to_string(CFStringRef cfstr) const;
        CFStringRef string_to_cfstring(const std::string& str) const;
        
        // Mach端口管理
        mach_port_t host_port_;
        
        // GCD队列管理器
        std::unique_ptr<GCDQueueManager> gcd_manager_;
        
        // Metal计算管理器
        std::unique_ptr<MetalComputeManager> metal_manager_;
        
        // 电源管理器
        std::unique_ptr<PowerManager> power_manager_;
        
        // IOKit连接
        io_connect_t io_master_port_;
        
        // 缓存的系统信息
        mutable std::mutex cache_mutex_;
        mutable std::optional<SystemInfo> cached_system_info_;
        mutable std::chrono::steady_clock::time_point cache_timestamp_;
        static constexpr std::chrono::seconds CACHE_DURATION{5};
        
        // 初始化状态
        std::atomic<bool> initialized_{false};
    };

    /**
     * @brief macOS平台特定工具函数
     */
    namespace utils {
        
        /**
         * @brief 执行AppleScript
         */
        std::optional<std::string> execute_applescript(const std::string& script);
        
        /**
         * @brief 获取应用程序包信息
         */
        struct AppBundleInfo {
            std::string bundle_id;
            std::string version;
            std::string short_version;
            std::string display_name;
            std::filesystem::path bundle_path;
        };
        std::optional<AppBundleInfo> get_app_bundle_info(const std::filesystem::path& app_path);
        
        /**
         * @brief 检查Dark Mode状态
         */
        bool is_dark_mode_enabled();
        
        /**
         * @brief 获取屏幕信息
         */
        struct ScreenInfo {
            int width = 0;
            int height = 0;
            double scale_factor = 1.0;
            int color_depth = 0;
            double refresh_rate = 0.0;
        };
        std::vector<ScreenInfo> get_screen_info();
        
        /**
         * @brief 检查辅助功能权限
         */
        bool has_accessibility_permissions();
        
        /**
         * @brief 请求辅助功能权限
         */
        bool request_accessibility_permissions();
        
        /**
         * @brief 获取系统偏好设置
         */
        std::optional<std::string> get_system_preference(const std::string& domain, 
                                                         const std::string& key);
        
        /**
         * @brief 设置系统偏好设置
         */
        bool set_system_preference(const std::string& domain, const std::string& key, 
                                 const std::string& value);
        
        /**
         * @brief 检查网络可达性
         */
        bool is_network_reachable(const std::string& hostname);
        
        /**
         * @brief 获取WiFi信息
         */
        struct WiFiInfo {
            std::string ssid;
            std::string bssid;
            int signal_strength = 0;
            std::string security_type;
            double link_speed = 0.0;
        };
        std::optional<WiFiInfo> get_wifi_info();
    }

} // namespace nex::platform::macos

#endif // HUSHELL_PLATFORM_MACOS