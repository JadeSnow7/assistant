#pragma once

#include "nex/platform/platform_adapter.hpp"
#include <fstream>
#include <sstream>

namespace nex::platform::unix {

    /**
     * @brief Unix/Linux平台适配器实现
     */
    class UnixPlatformAdapter : public IPlatformAdapter {
    public:
        UnixPlatformAdapter() = default;
        ~UnixPlatformAdapter() override = default;

        // ========== 进程管理 ==========
        std::vector<ProcessInfo> get_processes() const override;
        std::optional<ProcessInfo> get_process_by_pid(int pid) const override;
        std::vector<ProcessInfo> find_processes_by_name(const std::string& name) const override;
        bool kill_process(int pid, int signal = 15) const override;
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

    private:
        // 辅助方法
        std::optional<ProcessInfo> parse_proc_stat(const std::filesystem::path& proc_path) const;
        std::string read_file_content(const std::filesystem::path& file_path) const;
        std::vector<std::string> split_string(const std::string& str, char delimiter) const;
        double parse_load_average() const;
        std::pair<double, double> get_memory_info() const;
        std::pair<double, double> get_disk_info(const std::filesystem::path& path = "/") const;
        double get_cpu_usage() const;
        std::chrono::seconds get_system_uptime() const;
    };

} // namespace nex::platform::unix