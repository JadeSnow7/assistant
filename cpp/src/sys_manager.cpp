#include "../include/sys_manager.hpp"
#include "../include/common.hpp"
#include <thread>
#include <mutex>
#include <condition_variable>
#include <fstream>
#include <sstream>
#include <iostream>
#include <algorithm>

#ifdef _WIN32
#include <windows.h>
#include <psapi.h>
#include <pdh.h>
#elif __linux__
#include <unistd.h>
#include <sys/sysinfo.h>
#include <sys/statvfs.h>
#include <fstream>
#include <dirent.h>
#elif __APPLE__
#include <sys/types.h>
#include <sys/sysctl.h>
#include <mach/mach.h>
#include <mach/vm_statistics.h>
#include <mach/mach_types.h>
#include <mach/mach_init.h>
#include <mach/mach_host.h>
#endif

namespace ai_assistant {

class SystemManager::Impl {
public:
    Impl() : monitoring_active_(false), max_cpu_usage_(80.0), max_memory_usage_(80.0) {}
    
    ~Impl() {
        stop_monitoring();
    }
    
    SystemInfo get_system_info() const {
        SystemInfo info;
        info.timestamp = std::chrono::system_clock::now();
        
        try {
            get_cpu_info(info);
            get_memory_info(info);
            get_disk_info(info);
            get_gpu_info_internal(info);
            get_os_info(info);
        } catch (const std::exception& e) {
            Logger::error("Failed to get system info: " + std::string(e.what()));
        }
        
        return info;
    }
    
    std::vector<ProcessInfo> get_processes() const {
        std::vector<ProcessInfo> processes;
        
        try {
#ifdef __linux__
            processes = get_linux_processes();
#elif _WIN32
            processes = get_windows_processes();
#elif __APPLE__
            processes = get_macos_processes();
#endif
        } catch (const std::exception& e) {
            Logger::error("Failed to get process list: " + std::string(e.what()));
        }
        
        return processes;
    }
    
    ProcessInfo get_process_info(int pid) const {
        ProcessInfo info;
        info.pid = pid;
        
        try {
#ifdef __linux__
            info = get_linux_process_info(pid);
#elif _WIN32
            info = get_windows_process_info(pid);
#elif __APPLE__
            info = get_macos_process_info(pid);
#endif
        } catch (const std::exception& e) {
            Logger::error("Failed to get process info for PID " + std::to_string(pid) + ": " + std::string(e.what()));
        }
        
        return info;
    }
    
    bool start_monitoring(int interval_ms) {
        if (monitoring_active_) {
            return true;
        }
        
        monitoring_active_ = true;
        monitoring_interval_ = interval_ms;
        
        monitoring_thread_ = std::thread([this]() {
            while (monitoring_active_) {
                auto info = get_system_info();
                
                std::lock_guard<std::mutex> lock(history_mutex_);
                system_history_.push_back(info);
                
                // 保留最近100个记录
                if (system_history_.size() > 100) {
                    system_history_.erase(system_history_.begin());
                }
                
                std::this_thread::sleep_for(std::chrono::milliseconds(monitoring_interval_));
            }
        });
        
        Logger::info("System monitoring started with interval: " + std::to_string(interval_ms) + "ms");
        return true;
    }
    
    void stop_monitoring() {
        if (!monitoring_active_) {
            return;
        }
        
        monitoring_active_ = false;
        
        if (monitoring_thread_.joinable()) {
            monitoring_thread_.join();
        }
        
        Logger::info("System monitoring stopped");
    }
    
    bool has_sufficient_resources(const std::string& model_name) const {
        auto info = get_system_info();
        
        // 根据模型名称判断资源需求
        double required_memory_gb = 2.0; // 默认需求
        double required_cpu = 20.0;      // 默认CPU使用率
        
        if (model_name.find("qwen3:4b") != std::string::npos) {
            required_memory_gb = 4.0;
            required_cpu = 30.0;
        } else if (model_name.find("llama") != std::string::npos) {
            required_memory_gb = 8.0;
            required_cpu = 50.0;
        }
        
        return (info.memory_free_gb >= required_memory_gb) && 
               (info.cpu_usage <= max_cpu_usage_ - required_cpu);
    }
    
    std::string get_recommended_model_type() const {
        auto info = get_system_info();
        
        // 基于系统资源推荐模型
        if (info.memory_free_gb >= 8.0 && info.cpu_cores >= 8) {
            return "large_local";
        } else if (info.memory_free_gb >= 4.0 && info.cpu_cores >= 4) {
            return "medium_local";
        } else {
            return "cloud";
        }
    }
    
    void set_resource_limits(double max_cpu_usage, double max_memory_usage) {
        max_cpu_usage_ = max_cpu_usage;
        max_memory_usage_ = max_memory_usage;
        Logger::info("Resource limits updated: CPU=" + std::to_string(max_cpu_usage) + 
                    "%, Memory=" + std::to_string(max_memory_usage) + "%");
    }
    
    std::vector<std::string> get_gpu_info() const {
        std::vector<std::string> gpu_info;
        
        try {
            // 尝试检测NVIDIA GPU
            if (system("nvidia-smi --query-gpu=name --format=csv,noheader,nounits > /tmp/gpu_info.txt 2>/dev/null") == 0) {
                std::ifstream file("/tmp/gpu_info.txt");
                std::string line;
                while (std::getline(file, line)) {
                    if (!line.empty()) {
                        gpu_info.push_back("NVIDIA: " + line);
                    }
                }
            }
            
            // TODO: 添加AMD GPU检测
            // TODO: 添加Intel GPU检测
            
        } catch (const std::exception& e) {
            Logger::warning("Failed to get GPU info: " + std::string(e.what()));
        }
        
        if (gpu_info.empty()) {
            gpu_info.push_back("No GPU detected or GPU info unavailable");
        }
        
        return gpu_info;
    }
    
    bool is_cuda_available() const {
        try {
            // 检查CUDA工具包
            int result = system("nvcc --version > /dev/null 2>&1");
            if (result == 0) {
                // 检查GPU
                result = system("nvidia-smi > /dev/null 2>&1");
                return (result == 0);
            }
        } catch (const std::exception& e) {
            Logger::debug("CUDA check failed: " + std::string(e.what()));
        }
        
        return false;
    }

private:
    bool monitoring_active_;
    int monitoring_interval_;
    std::thread monitoring_thread_;
    std::vector<SystemInfo> system_history_;
    mutable std::mutex history_mutex_;
    double max_cpu_usage_;
    double max_memory_usage_;
    
    void get_cpu_info(SystemInfo& info) const {
#ifdef __linux__
        get_linux_cpu_info(info);
#elif _WIN32
        get_windows_cpu_info(info);
#elif __APPLE__
        get_macos_cpu_info(info);
#else
        // 默认值
        info.cpu_cores = std::thread::hardware_concurrency();
        info.cpu_usage = 0.0;
#endif
    }
    
    void get_memory_info(SystemInfo& info) const {
#ifdef __linux__
        get_linux_memory_info(info);
#elif _WIN32
        get_windows_memory_info(info);
#elif __APPLE__
        get_macos_memory_info(info);
#endif
    }
    
    void get_disk_info(SystemInfo& info) const {
#ifdef __linux__
        get_linux_disk_info(info);
#elif _WIN32
        get_windows_disk_info(info);
#elif __APPLE__
        get_macos_disk_info(info);
#endif
    }
    
    void get_gpu_info_internal(SystemInfo& info) const {
        // GPU信息获取较复杂，暂时设置默认值
        info.gpu_usage = 0.0;
        info.gpu_memory_usage = 0.0;
    }
    
    void get_os_info(SystemInfo& info) const {
#ifdef __linux__
        info.os_info = "Linux";
        
        std::ifstream file("/etc/os-release");
        std::string line;
        while (std::getline(file, line)) {
            if (line.find("PRETTY_NAME=") == 0) {
                info.os_info = line.substr(13);
                // 移除引号
                info.os_info.erase(std::remove(info.os_info.begin(), info.os_info.end(), '"'), info.os_info.end());
                break;
            }
        }
#elif _WIN32
        info.os_info = "Windows";
#elif __APPLE__
        info.os_info = "macOS";
#else
        info.os_info = "Unknown OS";
#endif
    }

#ifdef __linux__
    void get_linux_cpu_info(SystemInfo& info) const {
        info.cpu_cores = std::thread::hardware_concurrency();
        
        // 读取CPU使用率
        std::ifstream file("/proc/stat");
        std::string line;
        if (std::getline(file, line)) {
            std::istringstream iss(line);
            std::string cpu;
            long user, nice, system, idle;
            iss >> cpu >> user >> nice >> system >> idle;
            
            long total = user + nice + system + idle;
            long used = total - idle;
            
            info.cpu_usage = total > 0 ? (double)used / total * 100.0 : 0.0;
        }
    }
    
    void get_linux_memory_info(SystemInfo& info) const {
        std::ifstream file("/proc/meminfo");
        std::string line;
        long total_kb = 0, free_kb = 0, available_kb = 0;
        
        while (std::getline(file, line)) {
            if (line.find("MemTotal:") == 0) {
                sscanf(line.c_str(), "MemTotal: %ld kB", &total_kb);
            } else if (line.find("MemFree:") == 0) {
                sscanf(line.c_str(), "MemFree: %ld kB", &free_kb);
            } else if (line.find("MemAvailable:") == 0) {
                sscanf(line.c_str(), "MemAvailable: %ld kB", &available_kb);
            }
        }
        
        info.memory_total_gb = total_kb / 1024.0 / 1024.0;
        info.memory_free_gb = (available_kb > 0 ? available_kb : free_kb) / 1024.0 / 1024.0;
        info.memory_usage = total_kb > 0 ? (double)(total_kb - free_kb) / total_kb * 100.0 : 0.0;
    }
    
    void get_linux_disk_info(SystemInfo& info) const {
        struct statvfs stat;
        if (statvfs("/", &stat) == 0) {
            double total_gb = (double)stat.f_blocks * stat.f_frsize / 1024.0 / 1024.0 / 1024.0;
            double free_gb = (double)stat.f_bavail * stat.f_frsize / 1024.0 / 1024.0 / 1024.0;
            
            info.disk_free_gb = free_gb;
            info.disk_usage = total_gb > 0 ? (total_gb - free_gb) / total_gb * 100.0 : 0.0;
        }
    }
    
    std::vector<ProcessInfo> get_linux_processes() const {
        std::vector<ProcessInfo> processes;
        
        DIR* proc_dir = opendir("/proc");
        if (!proc_dir) return processes;
        
        struct dirent* entry;
        while ((entry = readdir(proc_dir)) != nullptr) {
            // 检查是否为数字目录（PID）
            if (std::all_of(entry->d_name, entry->d_name + strlen(entry->d_name), ::isdigit)) {
                int pid = std::atoi(entry->d_name);
                auto info = get_linux_process_info(pid);
                if (info.pid > 0) {
                    processes.push_back(info);
                }
            }
        }
        
        closedir(proc_dir);
        return processes;
    }
    
    ProcessInfo get_linux_process_info(int pid) const {
        ProcessInfo info;
        info.pid = pid;
        
        // 读取进程状态
        std::string stat_path = "/proc/" + std::to_string(pid) + "/stat";
        std::ifstream stat_file(stat_path);
        if (stat_file.is_open()) {
            std::string line;
            if (std::getline(stat_file, line)) {
                std::istringstream iss(line);
                std::string pid_str, comm, state;
                iss >> pid_str >> comm >> state;
                
                info.name = comm;
                info.status = state;
            }
        }
        
        // 读取内存使用
        std::string statm_path = "/proc/" + std::to_string(pid) + "/statm";
        std::ifstream statm_file(statm_path);
        if (statm_file.is_open()) {
            long size, resident;
            statm_file >> size >> resident;
            info.memory_usage_mb = resident * 4.0 / 1024.0; // 假设页面大小为4KB
        }
        
        return info;
    }
#endif

#ifdef _WIN32
    void get_windows_cpu_info(SystemInfo& info) const {
        SYSTEM_INFO sysInfo;
        GetSystemInfo(&sysInfo);
        info.cpu_cores = sysInfo.dwNumberOfProcessors;
        
        // TODO: 实现Windows CPU使用率获取
        info.cpu_usage = 0.0;
    }
    
    void get_windows_memory_info(SystemInfo& info) const {
        MEMORYSTATUSEX memInfo;
        memInfo.dwLength = sizeof(MEMORYSTATUSEX);
        GlobalMemoryStatusEx(&memInfo);
        
        info.memory_total_gb = memInfo.ullTotalPhys / 1024.0 / 1024.0 / 1024.0;
        info.memory_free_gb = memInfo.ullAvailPhys / 1024.0 / 1024.0 / 1024.0;
        info.memory_usage = memInfo.dwMemoryLoad;
    }
    
    void get_windows_disk_info(SystemInfo& info) const {
        ULARGE_INTEGER freeBytesAvailable, totalNumberOfBytes;
        if (GetDiskFreeSpaceEx(L"C:\\", &freeBytesAvailable, &totalNumberOfBytes, NULL)) {
            double total_gb = totalNumberOfBytes.QuadPart / 1024.0 / 1024.0 / 1024.0;
            double free_gb = freeBytesAvailable.QuadPart / 1024.0 / 1024.0 / 1024.0;
            
            info.disk_free_gb = free_gb;
            info.disk_usage = total_gb > 0 ? (total_gb - free_gb) / total_gb * 100.0 : 0.0;
        }
    }
    
    std::vector<ProcessInfo> get_windows_processes() const {
        // TODO: 实现Windows进程列表获取
        return {};
    }
    
    ProcessInfo get_windows_process_info(int pid) const {
        // TODO: 实现Windows进程信息获取
        ProcessInfo info;
        info.pid = pid;
        return info;
    }
#endif

#ifdef __APPLE__
    void get_macos_cpu_info(SystemInfo& info) const {
        // TODO: 实现macOS CPU信息获取
        info.cpu_cores = std::thread::hardware_concurrency();
        info.cpu_usage = 0.0;
    }
    
    void get_macos_memory_info(SystemInfo& info) const {
        // TODO: 实现macOS内存信息获取
        info.memory_total_gb = 0.0;
        info.memory_free_gb = 0.0;
        info.memory_usage = 0.0;
    }
    
    void get_macos_disk_info(SystemInfo& info) const {
        // TODO: 实现macOS磁盘信息获取
        info.disk_free_gb = 0.0;
        info.disk_usage = 0.0;
    }
    
    std::vector<ProcessInfo> get_macos_processes() const {
        // TODO: 实现macOS进程列表获取
        return {};
    }
    
    ProcessInfo get_macos_process_info(int pid) const {
        // TODO: 实现macOS进程信息获取
        ProcessInfo info;
        info.pid = pid;
        return info;
    }
#endif
};

// SystemManager公共接口实现
SystemManager::SystemManager() : pimpl_(std::make_unique<Impl>()) {}

SystemManager::~SystemManager() = default;

SystemInfo SystemManager::get_system_info() const {
    return pimpl_->get_system_info();
}

std::vector<ProcessInfo> SystemManager::get_processes() const {
    return pimpl_->get_processes();
}

ProcessInfo SystemManager::get_process_info(int pid) const {
    return pimpl_->get_process_info(pid);
}

bool SystemManager::start_monitoring(int interval_ms) {
    return pimpl_->start_monitoring(interval_ms);
}

void SystemManager::stop_monitoring() {
    pimpl_->stop_monitoring();
}

bool SystemManager::has_sufficient_resources(const std::string& model_name) const {
    return pimpl_->has_sufficient_resources(model_name);
}

std::string SystemManager::get_recommended_model_type() const {
    return pimpl_->get_recommended_model_type();
}

void SystemManager::set_resource_limits(double max_cpu_usage, double max_memory_usage) {
    pimpl_->set_resource_limits(max_cpu_usage, max_memory_usage);
}

std::vector<std::string> SystemManager::get_gpu_info() const {
    return pimpl_->get_gpu_info();
}

bool SystemManager::is_cuda_available() const {
    return pimpl_->is_cuda_available();
}

} // namespace ai_assistant