#include "nex/platform/unix_platform_adapter.hpp"
#include <iostream>
#include <fstream>
#include <sstream>
#include <algorithm>
#include <signal.h>
#include <unistd.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <sys/sysinfo.h>
#include <dirent.h>
#include <cstdlib>
#include <cstring>
#include <ifaddrs.h>
#include <netinet/in.h>
#include <arpa/inet.h>

namespace nex::platform::unix {

    std::vector<ProcessInfo> UnixPlatformAdapter::get_processes() const {
        std::vector<ProcessInfo> processes;
        
        try {
            for (const auto& entry : std::filesystem::directory_iterator("/proc")) {
                if (entry.is_directory()) {
                    const auto filename = entry.path().filename().string();
                    if (!filename.empty() && std::isdigit(filename[0])) {
                        auto process = parse_proc_stat(entry.path());
                        if (process) {
                            processes.push_back(*process);
                        }
                    }
                }
            }
        } catch (const std::exception& e) {
            // 记录错误但继续返回已收集的进程
            std::cerr << "获取进程列表时出错: " << e.what() << std::endl;
        }
        
        return processes;
    }

    std::optional<ProcessInfo> UnixPlatformAdapter::get_process_by_pid(int pid) const {
        const auto proc_path = std::filesystem::path("/proc") / std::to_string(pid);
        if (std::filesystem::exists(proc_path)) {
            return parse_proc_stat(proc_path);
        }
        return std::nullopt;
    }

    std::vector<ProcessInfo> UnixPlatformAdapter::find_processes_by_name(const std::string& name) const {
        std::vector<ProcessInfo> matching_processes;
        auto all_processes = get_processes();
        
        std::copy_if(all_processes.begin(), all_processes.end(),
                    std::back_inserter(matching_processes),
                    [&name](const ProcessInfo& process) {
                        return process.name.find(name) != std::string::npos;
                    });
        
        return matching_processes;
    }

    bool UnixPlatformAdapter::kill_process(int pid, int signal) const {
        return ::kill(pid, signal) == 0;
    }

    std::optional<ProcessInfo> UnixPlatformAdapter::start_process(
        const std::string& command,
        const std::filesystem::path& working_dir
    ) const {
        pid_t pid = fork();
        
        if (pid == -1) {
            return std::nullopt; // Fork失败
        }
        
        if (pid == 0) {
            // 子进程
            if (chdir(working_dir.c_str()) != 0) {
                exit(EXIT_FAILURE);
            }
            
            execl("/bin/sh", "sh", "-c", command.c_str(), nullptr);
            exit(EXIT_FAILURE); // execl失败
        }
        
        // 父进程 - 等待一小段时间确保子进程启动成功
        usleep(100000); // 100ms
        
        return get_process_by_pid(pid);
    }

    SystemInfo UnixPlatformAdapter::get_system_info() const {
        SystemInfo info;
        
        // 主机名
        char hostname[256];
        if (gethostname(hostname, sizeof(hostname)) == 0) {
            info.hostname = hostname;
        }
        
        // 系统信息
        struct utsname uname_data;
        if (uname(&uname_data) == 0) {
            info.os_name = uname_data.sysname;
            info.os_version = uname_data.release;
            info.architecture = uname_data.machine;
        }
        
        // CPU信息
        info.cpu_cores = std::thread::hardware_concurrency();
        info.cpu_threads = info.cpu_cores; // 简化处理，实际可能不同
        info.cpu_usage = get_cpu_usage();
        
        // 从/proc/cpuinfo读取CPU型号
        std::ifstream cpuinfo("/proc/cpuinfo");
        std::string line;
        while (std::getline(cpuinfo, line)) {
            if (line.find("model name") != std::string::npos) {
                auto pos = line.find(':');
                if (pos != std::string::npos) {
                    info.cpu_model = line.substr(pos + 2);
                    break;
                }
            }
        }
        
        // 内存信息
        auto [total_mem, available_mem] = get_memory_info();
        info.memory_total_gb = total_mem;
        info.memory_available_gb = available_mem;
        info.memory_usage = ((total_mem - available_mem) / total_mem) * 100.0;
        
        // 磁盘信息
        auto [total_disk, available_disk] = get_disk_info();
        info.disk_total_gb = total_disk;
        info.disk_available_gb = available_disk;
        info.disk_usage = ((total_disk - available_disk) / total_disk) * 100.0;
        
        // 系统负载
        double load_avg[3];
        if (getloadavg(load_avg, 3) != -1) {
            info.load_average_1min = load_avg[0];
            info.load_average_5min = load_avg[1];
            info.load_average_15min = load_avg[2];
        }
        
        // 系统运行时间
        info.uptime = get_system_uptime();
        
        return info;
    }

    std::vector<GpuInfo> UnixPlatformAdapter::get_gpu_info() const {
        std::vector<GpuInfo> gpus;
        
        // 尝试通过nvidia-smi获取NVIDIA GPU信息
        if (system("which nvidia-smi > /dev/null 2>&1") == 0) {
            // 简化实现 - 实际应解析nvidia-smi输出
            GpuInfo gpu;
            gpu.name = "NVIDIA GPU";
            gpu.vendor = "NVIDIA";
            gpu.cuda_supported = true;
            gpus.push_back(gpu);
        }
        
        return gpus;
    }

    std::optional<std::string> UnixPlatformAdapter::get_environment_variable(const std::string& name) const {
        const char* value = std::getenv(name.c_str());
        if (value) {
            return std::string(value);
        }
        return std::nullopt;
    }

    bool UnixPlatformAdapter::set_environment_variable(const std::string& name, const std::string& value) const {
        return setenv(name.c_str(), value.c_str(), 1) == 0;
    }

    std::filesystem::path UnixPlatformAdapter::get_temp_directory() const {
        auto tmp_dir = get_environment_variable("TMPDIR");
        if (tmp_dir) {
            return std::filesystem::path(*tmp_dir);
        }
        return std::filesystem::path("/tmp");
    }

    std::filesystem::path UnixPlatformAdapter::get_home_directory() const {
        auto home_dir = get_environment_variable("HOME");
        if (home_dir) {
            return std::filesystem::path(*home_dir);
        }
        return std::filesystem::current_path();
    }

    std::filesystem::path UnixPlatformAdapter::get_config_directory() const {
        auto xdg_config = get_environment_variable("XDG_CONFIG_HOME");
        if (xdg_config) {
            return std::filesystem::path(*xdg_config) / "nex";
        }
        return get_home_directory() / ".config" / "nex";
    }

    std::filesystem::path UnixPlatformAdapter::get_library_directory() const {
        return std::filesystem::path("/usr/lib");
    }

    bool UnixPlatformAdapter::is_executable(const std::filesystem::path& path) const {
        return access(path.c_str(), X_OK) == 0;
    }

    bool UnixPlatformAdapter::set_file_permissions(const std::filesystem::path& path, int permissions) const {
        return chmod(path.c_str(), permissions) == 0;
    }

    std::vector<NetworkInterface> UnixPlatformAdapter::get_network_interfaces() const {
        std::vector<NetworkInterface> interfaces;
        
        struct ifaddrs *ifaddr, *ifa;
        if (getifaddrs(&ifaddr) == -1) {
            return interfaces;
        }
        
        for (ifa = ifaddr; ifa != nullptr; ifa = ifa->ifa_next) {
            if (ifa->ifa_addr == nullptr) continue;
            
            NetworkInterface iface;
            iface.name = ifa->ifa_name;
            iface.is_up = (ifa->ifa_flags & IFF_UP) != 0;
            iface.is_loopback = (ifa->ifa_flags & IFF_LOOPBACK) != 0;
            
            if (ifa->ifa_addr->sa_family == AF_INET) {
                struct sockaddr_in* sin = (struct sockaddr_in*)ifa->ifa_addr;
                iface.ip_address = inet_ntoa(sin->sin_addr);
                
                if (ifa->ifa_netmask) {
                    struct sockaddr_in* netmask = (struct sockaddr_in*)ifa->ifa_netmask;
                    iface.netmask = inet_ntoa(netmask->sin_addr);
                }
                
                interfaces.push_back(iface);
            }
        }
        
        freeifaddrs(ifaddr);
        return interfaces;
    }

    bool UnixPlatformAdapter::is_port_available(int port, const std::string& protocol) const {
        // 简化实现 - 实际应检查端口占用情况
        std::string cmd = "netstat -ln | grep :" + std::to_string(port) + " > /dev/null 2>&1";
        return system(cmd.c_str()) != 0; // 如果找不到端口，说明可用
    }

    std::vector<std::string> UnixPlatformAdapter::get_local_ip_addresses() const {
        std::vector<std::string> addresses;
        auto interfaces = get_network_interfaces();
        
        for (const auto& iface : interfaces) {
            if (!iface.is_loopback && iface.is_up && !iface.ip_address.empty()) {
                addresses.push_back(iface.ip_address);
            }
        }
        
        return addresses;
    }

    bool UnixPlatformAdapter::is_cuda_available() const {
        return system("which nvcc > /dev/null 2>&1") == 0 ||
               system("ls /usr/local/cuda/bin/nvcc > /dev/null 2>&1") == 0;
    }

    bool UnixPlatformAdapter::is_opencl_available() const {
        return std::filesystem::exists("/usr/lib/libOpenCL.so") ||
               std::filesystem::exists("/usr/lib64/libOpenCL.so");
    }

    std::optional<double> UnixPlatformAdapter::get_cpu_temperature() const {
        // 尝试从thermal_zone读取温度
        for (int i = 0; i < 10; ++i) {
            std::string temp_file = "/sys/class/thermal/thermal_zone" + std::to_string(i) + "/temp";
            std::ifstream temp_stream(temp_file);
            if (temp_stream.is_open()) {
                int temp_millicelsius;
                temp_stream >> temp_millicelsius;
                return temp_millicelsius / 1000.0;
            }
        }
        return std::nullopt;
    }

    // ========== 私有辅助方法 ==========

    std::optional<ProcessInfo> UnixPlatformAdapter::parse_proc_stat(const std::filesystem::path& proc_path) const {
        try {
            ProcessInfo info;
            
            // 从stat文件读取进程信息
            std::ifstream stat_file(proc_path / "stat");
            if (!stat_file.is_open()) {
                return std::nullopt;
            }
            
            std::string line;
            std::getline(stat_file, line);
            std::istringstream iss(line);
            
            std::string pid_str, comm, state;
            iss >> pid_str >> comm >> state;
            
            info.pid = std::stoi(pid_str);
            info.name = comm.substr(1, comm.length() - 2); // 去掉括号
            info.status = state;
            
            // 尝试读取cmdline
            std::ifstream cmdline_file(proc_path / "cmdline");
            if (cmdline_file.is_open()) {
                std::getline(cmdline_file, info.command_line);
                // 替换null字符为空格
                std::replace(info.command_line.begin(), info.command_line.end(), '\0', ' ');
            }
            
            return info;
        } catch (const std::exception&) {
            return std::nullopt;
        }
    }

    std::string UnixPlatformAdapter::read_file_content(const std::filesystem::path& file_path) const {
        std::ifstream file(file_path);
        if (!file.is_open()) {
            return "";
        }
        
        std::ostringstream content;
        content << file.rdbuf();
        return content.str();
    }

    std::vector<std::string> UnixPlatformAdapter::split_string(const std::string& str, char delimiter) const {
        std::vector<std::string> tokens;
        std::istringstream iss(str);
        std::string token;
        
        while (std::getline(iss, token, delimiter)) {
            if (!token.empty()) {
                tokens.push_back(token);
            }
        }
        
        return tokens;
    }

    std::pair<double, double> UnixPlatformAdapter::get_memory_info() const {
        std::ifstream meminfo("/proc/meminfo");
        std::string line;
        double total_kb = 0, available_kb = 0;
        
        while (std::getline(meminfo, line)) {
            if (line.find("MemTotal:") == 0) {
                std::istringstream iss(line);
                std::string label, value, unit;
                iss >> label >> value >> unit;
                total_kb = std::stod(value);
            } else if (line.find("MemAvailable:") == 0) {
                std::istringstream iss(line);
                std::string label, value, unit;
                iss >> label >> value >> unit;
                available_kb = std::stod(value);
            }
        }
        
        return {total_kb / 1024.0 / 1024.0, available_kb / 1024.0 / 1024.0}; // 转换为GB
    }

    std::pair<double, double> UnixPlatformAdapter::get_disk_info(const std::filesystem::path& path) const {
        try {
            auto space = std::filesystem::space(path);
            double total_gb = space.capacity / (1024.0 * 1024.0 * 1024.0);
            double available_gb = space.available / (1024.0 * 1024.0 * 1024.0);
            return {total_gb, available_gb};
        } catch (const std::exception&) {
            return {0.0, 0.0};
        }
    }

    double UnixPlatformAdapter::get_cpu_usage() const {
        // 简化的CPU使用率计算，实际应该计算两次采样的差值
        std::ifstream stat_file("/proc/stat");
        std::string line;
        std::getline(stat_file, line);
        
        // 解析第一行CPU统计信息
        std::istringstream iss(line);
        std::string cpu_label;
        long long user, nice, system, idle;
        iss >> cpu_label >> user >> nice >> system >> idle;
        
        long long total = user + nice + system + idle;
        if (total > 0) {
            return ((total - idle) * 100.0) / total;
        }
        
        return 0.0;
    }

    std::chrono::seconds UnixPlatformAdapter::get_system_uptime() const {
        std::ifstream uptime_file("/proc/uptime");
        double uptime_seconds;
        if (uptime_file >> uptime_seconds) {
            return std::chrono::seconds(static_cast<long long>(uptime_seconds));
        }
        return std::chrono::seconds(0);
    }

} // namespace nex::platform::unix