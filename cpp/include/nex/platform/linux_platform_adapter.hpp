#pragma once

#include "platform_adapter.hpp"
#include "../platform_config.h"

#ifdef HUSHELL_PLATFORM_LINUX

#include <sys/epoll.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <unistd.h>
#include <numa.h>
#include <thread>
#include <vector>
#include <memory>

namespace nex::platform::linux {

    /**
     * @brief Linux平台特定性能计数器
     */
    struct LinuxPerfCounters {
        uint64_t cpu_cycles = 0;
        uint64_t instructions = 0;
        uint64_t cache_misses = 0;
        uint64_t branch_misses = 0;
        uint64_t page_faults = 0;
        uint64_t context_switches = 0;
    };

    /**
     * @brief NUMA节点信息
     */
    struct NUMANodeInfo {
        int node_id = -1;
        size_t memory_size_mb = 0;
        size_t available_memory_mb = 0;
        std::vector<int> cpu_list;
        double memory_bandwidth_gbps = 0.0;
        double latency_ns = 0.0;
    };

    /**
     * @brief epoll事件监控器
     */
    class EpollMonitor {
    public:
        EpollMonitor();
        ~EpollMonitor();

        /**
         * @brief 添加文件描述符监控
         */
        bool add_fd(int fd, uint32_t events);

        /**
         * @brief 移除文件描述符监控
         */
        bool remove_fd(int fd);

        /**
         * @brief 等待事件
         */
        int wait_for_events(struct epoll_event* events, int max_events, int timeout_ms);

        /**
         * @brief 获取epoll文件描述符
         */
        int get_epoll_fd() const;

    private:
        int epoll_fd_;
    };

    /**
     * @brief Linux平台适配器实现
     */
    class LinuxPlatformAdapter : public IPlatformAdapter {
    public:
        LinuxPlatformAdapter();
        virtual ~LinuxPlatformAdapter();

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

        // ========== Linux特定功能 ==========

        /**
         * @brief 设置epoll监控
         */
        void setup_epoll_monitoring();

        /**
         * @brief NUMA感知内存分配
         */
        void* allocate_numa_memory(size_t size, int node);

        /**
         * @brief 释放NUMA内存
         */
        void deallocate_numa_memory(void* ptr, size_t size);

        /**
         * @brief 获取Linux性能计数器
         */
        LinuxPerfCounters get_perf_counters() const;

        /**
         * @brief 设置CPU亲和性
         */
        bool set_cpu_affinity(const std::vector<int>& cpus);

        /**
         * @brief 获取当前CPU亲和性
         */
        std::vector<int> get_cpu_affinity() const;

        /**
         * @brief 获取NUMA拓扑信息
         */
        std::vector<NUMANodeInfo> get_numa_topology() const;

        /**
         * @brief 设置进程优先级
         */
        bool set_process_priority(int pid, int priority);

        /**
         * @brief 设置进程调度策略
         */
        bool set_scheduling_policy(int pid, int policy, int priority);

        /**
         * @brief 获取系统负载
         */
        std::tuple<double, double, double> get_load_average() const;

        /**
         * @brief 获取内存信息
         */
        struct MemoryInfo {
            size_t total_mb = 0;
            size_t available_mb = 0;
            size_t free_mb = 0;
            size_t buffers_mb = 0;
            size_t cached_mb = 0;
            size_t swap_total_mb = 0;
            size_t swap_free_mb = 0;
        };
        MemoryInfo get_memory_info() const;

        /**
         * @brief 获取CPU使用率
         */
        double get_cpu_usage() const;

        /**
         * @brief 获取磁盘I/O统计
         */
        struct DiskIOStats {
            uint64_t read_bytes = 0;
            uint64_t write_bytes = 0;
            uint64_t read_ops = 0;
            uint64_t write_ops = 0;
            double read_time_ms = 0.0;
            double write_time_ms = 0.0;
        };
        std::unordered_map<std::string, DiskIOStats> get_disk_io_stats() const;

        /**
         * @brief 获取网络I/O统计
         */
        struct NetworkIOStats {
            uint64_t rx_bytes = 0;
            uint64_t tx_bytes = 0;
            uint64_t rx_packets = 0;
            uint64_t tx_packets = 0;
            uint64_t rx_errors = 0;
            uint64_t tx_errors = 0;
        };
        std::unordered_map<std::string, NetworkIOStats> get_network_io_stats() const;

        /**
         * @brief 启用性能优化
         */
        void optimize_for_platform() override;

        /**
         * @brief 配置透明大页面
         */
        bool configure_transparent_hugepages(bool enable);

        /**
         * @brief 检查容器环境
         */
        bool is_running_in_container() const;

        /**
         * @brief 获取容器类型
         */
        std::string get_container_type() const;

    private:
        // 内部实现方法
        ProcessInfo parse_proc_stat(int pid) const;
        ProcessInfo parse_proc_status(int pid) const;
        std::string read_file_content(const std::filesystem::path& path) const;
        std::vector<std::string> split_string(const std::string& str, char delimiter) const;
        
        // 性能监控
        void initialize_perf_counters();
        void cleanup_perf_counters();
        
        // NUMA支持
        bool initialize_numa();
        void cleanup_numa();
        
        // epoll监控
        std::unique_ptr<EpollMonitor> epoll_monitor_;
        
        // 性能计数器文件描述符
        std::vector<int> perf_event_fds_;
        
        // NUMA状态
        bool numa_available_;
        std::vector<NUMANodeInfo> numa_nodes_;
        
        // 缓存的系统信息
        mutable std::mutex cache_mutex_;
        mutable std::optional<SystemInfo> cached_system_info_;
        mutable std::chrono::steady_clock::time_point cache_timestamp_;
        static constexpr std::chrono::seconds CACHE_DURATION{5};
        
        // 初始化状态
        std::atomic<bool> initialized_{false};
    };

    /**
     * @brief Linux平台特定工具函数
     */
    namespace utils {
        
        /**
         * @brief 解析/proc/stat文件
         */
        std::unordered_map<std::string, uint64_t> parse_proc_stat();
        
        /**
         * @brief 解析/proc/meminfo文件
         */
        std::unordered_map<std::string, uint64_t> parse_proc_meminfo();
        
        /**
         * @brief 解析/proc/loadavg文件
         */
        std::tuple<double, double, double> parse_proc_loadavg();
        
        /**
         * @brief 检查文件是否存在
         */
        bool file_exists(const std::filesystem::path& path);
        
        /**
         * @brief 安全读取文件内容
         */
        std::optional<std::string> safe_read_file(const std::filesystem::path& path);
        
        /**
         * @brief 执行系统命令并获取输出
         */
        std::optional<std::string> execute_command(const std::string& command);
        
        /**
         * @brief 解析网络接口信息
         */
        std::vector<NetworkInterface> parse_network_interfaces();
        
        /**
         * @brief 检查端口占用
         */
        bool is_port_in_use(int port, const std::string& protocol);
        
        /**
         * @brief 获取GPU设备信息（通过nvidia-ml）
         */
        std::vector<GpuInfo> get_nvidia_gpu_info();
        
        /**
         * @brief 获取AMD GPU信息
         */
        std::vector<GpuInfo> get_amd_gpu_info();
        
        /**
         * @brief 获取Intel GPU信息
         */
        std::vector<GpuInfo> get_intel_gpu_info();
    }

} // namespace nex::platform::linux

#endif // HUSHELL_PLATFORM_LINUX