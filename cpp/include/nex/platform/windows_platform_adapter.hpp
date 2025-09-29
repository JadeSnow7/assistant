#pragma once

#include "platform_adapter.hpp"
#include "../platform_config.h"

#ifdef HUSHELL_PLATFORM_WINDOWS

#include <windows.h>
#include <winsock2.h>
#include <ws2tcpip.h>
#include <iphlpapi.h>
#include <psapi.h>
#include <tlhelp32.h>
#include <pdh.h>
#include <memory>
#include <vector>

namespace nex::platform::windows {

    /**
     * @brief Windows性能计数器
     */
    struct WindowsPerfCounters {
        double cpu_usage = 0.0;
        double memory_usage = 0.0;
        double disk_usage = 0.0;
        double network_usage = 0.0;
        uint64_t page_faults = 0;
        uint64_t context_switches = 0;
    };

    /**
     * @brief IOCP（I/O完成端口）管理器
     */
    class IOCPManager {
    public:
        IOCPManager();
        ~IOCPManager();

        /**
         * @brief 创建IOCP
         */
        bool create_iocp(DWORD max_concurrent_threads = 0);

        /**
         * @brief 关联文件句柄到IOCP
         */
        bool associate_handle(HANDLE handle, ULONG_PTR completion_key);

        /**
         * @brief 获取完成状态
         */
        bool get_completion_status(DWORD timeout_ms, DWORD& bytes_transferred, 
                                 ULONG_PTR& completion_key, OVERLAPPED*& overlapped);

        /**
         * @brief 投递完成状态
         */
        bool post_completion_status(DWORD bytes_transferred, ULONG_PTR completion_key, 
                                  OVERLAPPED* overlapped);

        /**
         * @brief 获取IOCP句柄
         */
        HANDLE get_handle() const;

    private:
        HANDLE iocp_handle_;
    };

    /**
     * @brief Windows事件追踪（ETW）管理器
     */
    class ETWTracing {
    public:
        ETWTracing();
        ~ETWTracing();

        /**
         * @brief 设置ETW追踪
         */
        bool setup_etw_tracing();

        /**
         * @brief 开始追踪
         */
        bool start_tracing();

        /**
         * @brief 停止追踪
         */
        bool stop_tracing();

        /**
         * @brief 记录事件
         */
        void log_event(const std::string& event_name, const std::string& data);

    private:
        TRACEHANDLE session_handle_;
        bool tracing_active_;
    };

    /**
     * @brief Windows平台适配器实现
     */
    class WindowsPlatformAdapter : public IPlatformAdapter {
    public:
        WindowsPlatformAdapter();
        virtual ~WindowsPlatformAdapter();

        // ========== 生命周期管理 ==========
        bool initialize();
        void shutdown();

        // ========== 进程管理 ==========
        std::vector<ProcessInfo> get_processes() const override;
        std::optional<ProcessInfo> get_process_by_pid(int pid) const override;
        std::vector<ProcessInfo> find_processes_by_name(const std::string& name) const override;
        bool kill_process(int pid, int signal = 0) const override;
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

        // ========== Windows特定功能 ==========

        /**
         * @brief 设置IOCP
         */
        void setup_iocp();

        /**
         * @brief 分配大页面内存
         */
        void* allocate_large_pages(size_t size);

        /**
         * @brief 释放大页面内存
         */
        void deallocate_large_pages(void* ptr);

        /**
         * @brief 设置ETW追踪
         */
        void setup_etw_tracing();

        /**
         * @brief 设置进程优先级
         */
        bool set_process_priority(ProcessPriority priority);

        /**
         * @brief 获取Windows性能计数器
         */
        WindowsPerfCounters get_perf_counters() const;

        /**
         * @brief 设置线程亲和性
         */
        bool set_thread_affinity(HANDLE thread, DWORD_PTR affinity_mask);

        /**
         * @brief 获取系统内存信息
         */
        struct WindowsMemoryInfo {
            DWORDLONG total_physical_mb = 0;
            DWORDLONG available_physical_mb = 0;
            DWORDLONG total_virtual_mb = 0;
            DWORDLONG available_virtual_mb = 0;
            DWORDLONG total_page_file_mb = 0;
            DWORDLONG available_page_file_mb = 0;
        };
        WindowsMemoryInfo get_windows_memory_info() const;

        /**
         * @brief 获取注册表值
         */
        std::optional<std::string> get_registry_value(HKEY root, const std::string& subkey, 
                                                     const std::string& value_name) const;

        /**
         * @brief 设置注册表值
         */
        bool set_registry_value(HKEY root, const std::string& subkey, 
                              const std::string& value_name, const std::string& value) const;

        /**
         * @brief 获取Windows版本信息
         */
        struct WindowsVersionInfo {
            DWORD major_version = 0;
            DWORD minor_version = 0;
            DWORD build_number = 0;
            std::string product_name;
            std::string edition;
            bool is_server = false;
        };
        WindowsVersionInfo get_windows_version_info() const;

        /**
         * @brief 检查权限
         */
        bool is_running_as_administrator() const;

        /**
         * @brief 请求管理员权限
         */
        bool request_administrator_privileges() const;

        /**
         * @brief 获取Windows服务状态
         */
        struct ServiceInfo {
            std::string name;
            std::string display_name;
            DWORD status = 0;
            DWORD start_type = 0;
        };
        std::vector<ServiceInfo> get_windows_services() const;

        /**
         * @brief 控制Windows服务
         */
        bool control_service(const std::string& service_name, DWORD control_code);

        /**
         * @brief 启用性能优化
         */
        void optimize_for_platform() override;

        /**
         * @brief 配置Windows高性能电源模式
         */
        bool set_high_performance_power_mode();

        /**
         * @brief 禁用Windows Defender实时保护（临时）
         */
        bool temporarily_disable_defender();

        /**
         * @brief 优化Windows调度器
         */
        bool optimize_scheduler_settings();

    private:
        // 内部实现方法
        ProcessInfo create_process_info_from_entry(const PROCESSENTRY32W& entry) const;
        std::string wide_to_string(const std::wstring& wide_str) const;
        std::wstring string_to_wide(const std::string& str) const;
        
        // 性能监控初始化
        bool initialize_pdh();
        void cleanup_pdh();
        
        // WMI初始化
        bool initialize_wmi();
        void cleanup_wmi();
        
        // DirectML检测
        bool detect_directml();
        
        // IOCP管理器
        std::unique_ptr<IOCPManager> iocp_manager_;
        
        // ETW追踪
        std::unique_ptr<ETWTracing> etw_tracing_;
        
        // PDH计数器句柄
        PDH_HQUERY pdh_query_;
        std::vector<PDH_HCOUNTER> pdh_counters_;
        
        // WMI接口
        void* wmi_services_;  // IWbemServices*
        
        // 缓存的系统信息
        mutable std::mutex cache_mutex_;
        mutable std::optional<SystemInfo> cached_system_info_;
        mutable std::chrono::steady_clock::time_point cache_timestamp_;
        static constexpr std::chrono::seconds CACHE_DURATION{5};
        
        // 初始化状态
        std::atomic<bool> initialized_{false};
        std::atomic<bool> winsock_initialized_{false};
    };

    /**
     * @brief Windows平台特定工具函数
     */
    namespace utils {
        
        /**
         * @brief 获取最后的Windows错误信息
         */
        std::string get_last_error_string();
        
        /**
         * @brief 检查Windows功能可用性
         */
        bool is_feature_available(const std::string& feature_name);
        
        /**
         * @brief 获取系统信息通过WMI
         */
        std::optional<std::string> get_wmi_property(const std::string& class_name, 
                                                   const std::string& property_name);
        
        /**
         * @brief 执行PowerShell命令
         */
        std::optional<std::string> execute_powershell(const std::string& command);
        
        /**
         * @brief 检查DirectX版本
         */
        std::string get_directx_version();
        
        /**
         * @brief 获取已安装的.NET Framework版本
         */
        std::vector<std::string> get_dotnet_versions();
        
        /**
         * @brief 检查Windows容器环境
         */
        bool is_running_in_container();
        
        /**
         * @brief 获取Windows容器类型
         */
        std::string get_container_type();
        
        /**
         * @brief 获取GPU信息通过DXGI
         */
        std::vector<GpuInfo> get_dxgi_gpu_info();
        
        /**
         * @brief 获取GPU信息通过WMI
         */
        std::vector<GpuInfo> get_wmi_gpu_info();
        
        /**
         * @brief 检查Hyper-V状态
         */
        bool is_hyperv_enabled();
    }

} // namespace nex::platform::windows

#endif // HUSHELL_PLATFORM_WINDOWS