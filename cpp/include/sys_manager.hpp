#pragma once

#include <string>
#include <map>
#include <vector>
#include <chrono>

namespace ai_assistant {

// 系统资源信息
struct SystemInfo {
    double cpu_usage = 0.0;        // CPU使用率 (%)
    double memory_usage = 0.0;     // 内存使用率 (%)
    double memory_total_gb = 0.0;  // 总内存 (GB)
    double memory_free_gb = 0.0;   // 可用内存 (GB)
    double disk_usage = 0.0;       // 磁盘使用率 (%)
    double disk_free_gb = 0.0;     // 可用磁盘空间 (GB)
    double gpu_usage = 0.0;        // GPU使用率 (%)
    double gpu_memory_usage = 0.0; // GPU内存使用率 (%)
    int cpu_cores = 0;             // CPU核心数
    std::string os_info;           // 操作系统信息
    std::chrono::system_clock::time_point timestamp;
};

// 进程信息
struct ProcessInfo {
    int pid = 0;
    std::string name;
    double cpu_usage = 0.0;
    double memory_usage_mb = 0.0;
    std::string status;
};

/**
 * 系统资源管理器
 * 跨平台系统监控和资源管理
 */
class SystemManager {
public:
    SystemManager();
    ~SystemManager();

    // 获取系统信息
    SystemInfo get_system_info() const;
    
    // 获取进程列表
    std::vector<ProcessInfo> get_processes() const;
    
    // 获取特定进程信息
    ProcessInfo get_process_info(int pid) const;
    
    // 启动监控
    bool start_monitoring(int interval_ms = 1000);
    
    // 停止监控
    void stop_monitoring();
    
    // 检查资源是否足够运行模型
    bool has_sufficient_resources(const std::string& model_name) const;
    
    // 获取推荐的模型类型
    std::string get_recommended_model_type() const;
    
    // 设置资源限制
    void set_resource_limits(double max_cpu_usage, double max_memory_usage);
    
    // 获取GPU信息
    std::vector<std::string> get_gpu_info() const;
    
    // 检查是否支持CUDA
    bool is_cuda_available() const;

private:
    class Impl;
    std::unique_ptr<Impl> pimpl_;
};

} // namespace ai_assistant