#pragma once

#include <vector>
#include <string>
#include <filesystem>
#include <chrono>
#include <optional>
#include <memory>

namespace nex::platform {

    /**
     * @brief 进程信息结构体
     */
    struct ProcessInfo {
        int pid;
        std::string name;
        std::string command_line;
        double cpu_usage = 0.0;
        size_t memory_usage_mb = 0;
        std::chrono::system_clock::time_point start_time;
        std::string status;
        int parent_pid = 0;
    };

    /**
     * @brief 系统信息结构体
     */
    struct SystemInfo {
        std::string hostname;
        std::string os_name;
        std::string os_version;
        std::string architecture;
        
        // CPU信息
        int cpu_cores = 0;
        int cpu_threads = 0;
        double cpu_usage = 0.0;
        std::string cpu_model;
        
        // 内存信息
        double memory_total_gb = 0.0;
        double memory_available_gb = 0.0;
        double memory_usage = 0.0;
        
        // 磁盘信息
        double disk_total_gb = 0.0;
        double disk_available_gb = 0.0;
        double disk_usage = 0.0;
        
        // 系统负载
        double load_average_1min = 0.0;
        double load_average_5min = 0.0;
        double load_average_15min = 0.0;
        
        // 运行时间
        std::chrono::seconds uptime{0};
    };

    /**
     * @brief 网络接口信息结构体
     */
    struct NetworkInterface {
        std::string name;
        std::string ip_address;
        std::string netmask;
        std::string mac_address;
        bool is_up = false;
        bool is_loopback = false;
        uint64_t bytes_sent = 0;
        uint64_t bytes_received = 0;
        uint64_t packets_sent = 0;
        uint64_t packets_received = 0;
    };

    /**
     * @brief GPU信息结构体
     */
    struct GpuInfo {
        std::string name;
        std::string vendor;
        std::string driver_version;
        size_t memory_total_mb = 0;
        size_t memory_used_mb = 0;
        double temperature = 0.0;
        double utilization = 0.0;
        bool cuda_supported = false;
        bool opencl_supported = false;
    };

    /**
     * @brief 平台适配器接口 - 提供跨平台的系统操作抽象
     */
    class IPlatformAdapter {
    public:
        virtual ~IPlatformAdapter() = default;
        
        // ========== 进程管理 ==========
        
        /**
         * @brief 获取所有进程列表
         * @return std::vector<ProcessInfo> 进程信息列表
         */
        virtual std::vector<ProcessInfo> get_processes() const = 0;
        
        /**
         * @brief 根据PID获取进程信息
         * @param pid 进程ID
         * @return std::optional<ProcessInfo> 进程信息，不存在则返回空
         */
        virtual std::optional<ProcessInfo> get_process_by_pid(int pid) const = 0;
        
        /**
         * @brief 根据名称查找进程
         * @param name 进程名称
         * @return std::vector<ProcessInfo> 匹配的进程列表
         */
        virtual std::vector<ProcessInfo> find_processes_by_name(const std::string& name) const = 0;
        
        /**
         * @brief 终止进程
         * @param pid 进程ID
         * @param signal 信号类型(Unix)或强制终止标志(Windows)
         * @return bool 操作是否成功
         */
        virtual bool kill_process(int pid, int signal = 15) const = 0;
        
        /**
         * @brief 启动新进程
         * @param command 命令行
         * @param working_dir 工作目录
         * @return std::optional<ProcessInfo> 启动的进程信息
         */
        virtual std::optional<ProcessInfo> start_process(
            const std::string& command,
            const std::filesystem::path& working_dir = std::filesystem::current_path()
        ) const = 0;
        
        // ========== 系统信息 ==========
        
        /**
         * @brief 获取系统信息
         * @return SystemInfo 系统信息
         */
        virtual SystemInfo get_system_info() const = 0;
        
        /**
         * @brief 获取GPU信息列表
         * @return std::vector<GpuInfo> GPU信息列表
         */
        virtual std::vector<GpuInfo> get_gpu_info() const = 0;
        
        /**
         * @brief 获取系统环境变量
         * @param name 环境变量名
         * @return std::optional<std::string> 环境变量值
         */
        virtual std::optional<std::string> get_environment_variable(const std::string& name) const = 0;
        
        /**
         * @brief 设置环境变量
         * @param name 环境变量名
         * @param value 环境变量值
         * @return bool 操作是否成功
         */
        virtual bool set_environment_variable(const std::string& name, const std::string& value) const = 0;
        
        // ========== 文件系统 ==========
        
        /**
         * @brief 获取临时目录路径
         * @return std::filesystem::path 临时目录路径
         */
        virtual std::filesystem::path get_temp_directory() const = 0;
        
        /**
         * @brief 获取用户主目录路径
         * @return std::filesystem::path 主目录路径
         */
        virtual std::filesystem::path get_home_directory() const = 0;
        
        /**
         * @brief 获取应用配置目录路径
         * @return std::filesystem::path 配置目录路径
         */
        virtual std::filesystem::path get_config_directory() const = 0;
        
        /**
         * @brief 获取系统库目录路径
         * @return std::filesystem::path 库目录路径
         */
        virtual std::filesystem::path get_library_directory() const = 0;
        
        /**
         * @brief 检查文件是否为可执行文件
         * @param path 文件路径
         * @return bool 是否为可执行文件
         */
        virtual bool is_executable(const std::filesystem::path& path) const = 0;
        
        /**
         * @brief 设置文件权限
         * @param path 文件路径
         * @param permissions 权限设置
         * @return bool 操作是否成功
         */
        virtual bool set_file_permissions(const std::filesystem::path& path, int permissions) const = 0;
        
        // ========== 网络 ==========
        
        /**
         * @brief 获取网络接口列表
         * @return std::vector<NetworkInterface> 网络接口列表
         */
        virtual std::vector<NetworkInterface> get_network_interfaces() const = 0;
        
        /**
         * @brief 检查端口是否可用
         * @param port 端口号
         * @param protocol 协议类型("tcp" 或 "udp")
         * @return bool 端口是否可用
         */
        virtual bool is_port_available(int port, const std::string& protocol = "tcp") const = 0;
        
        /**
         * @brief 获取本机IP地址
         * @return std::vector<std::string> IP地址列表
         */
        virtual std::vector<std::string> get_local_ip_addresses() const = 0;
        
        // ========== 硬件信息 ==========
        
        /**
         * @brief 检查CUDA是否可用
         * @return bool CUDA是否可用
         */
        virtual bool is_cuda_available() const = 0;
        
        /**
         * @brief 检查OpenCL是否可用
         * @return bool OpenCL是否可用
         */
        virtual bool is_opencl_available() const = 0;
        
        /**
         * @brief 获取CPU温度（如果支持）
         * @return std::optional<double> CPU温度（摄氏度）
         */
        virtual std::optional<double> get_cpu_temperature() const = 0;
    };

} // namespace nex::platform