#pragma once

#include "common.hpp"
#include <future>
#include <thread>
#include <atomic>
#include <condition_variable>
#include <queue>
#include <functional>
#include <vector>
#include <memory>

namespace ai_assistant {

// 任务优先级
enum class TaskPriority {
    LOW = 0,
    NORMAL = 1,
    HIGH = 2,
    CRITICAL = 3
};

// 任务状态
enum class TaskStatus {
    PENDING,
    RUNNING,
    COMPLETED,
    FAILED,
    CANCELLED
};

// 任务信息
struct TaskInfo {
    std::string task_id;
    TaskPriority priority;
    TaskStatus status;
    std::chrono::steady_clock::time_point created_time;
    std::chrono::steady_clock::time_point start_time;
    std::chrono::steady_clock::time_point end_time;
    std::chrono::milliseconds execution_time;
    std::string error_message;
    size_t retry_count;
    size_t max_retries;
};

// 异步任务调度器
class AsyncTaskScheduler {
public:
    AsyncTaskScheduler(size_t thread_count = std::thread::hardware_concurrency());
    ~AsyncTaskScheduler();
    
    // 提交任务
    template<typename F, typename... Args>
    auto submit_task(TaskPriority priority, F&& f, Args&&... args) 
        -> std::future<typename std::result_of<F(Args...)>::type>;
    
    // 提交带ID的任务
    template<typename F, typename... Args>
    auto submit_task_with_id(const std::string& task_id, TaskPriority priority, F&& f, Args&&... args)
        -> std::future<typename std::result_of<F(Args...)>::type>;
    
    // 提交可重试的任务
    template<typename F, typename... Args>
    auto submit_retryable_task(TaskPriority priority, size_t max_retries, F&& f, Args&&... args)
        -> std::future<typename std::result_of<F(Args...)>::type>;
    
    // 启动调度器
    void start();
    
    // 停止调度器
    void stop();
    
    // 暂停任务处理
    void pause();
    
    // 恢复任务处理
    void resume();
    
    // 取消任务
    bool cancel_task(const std::string& task_id);
    
    // 设置工作线程数
    void set_worker_count(size_t count);
    
    // 获取任务统计信息
    struct TaskStatistics {
        size_t pending_tasks;
        size_t running_tasks;
        size_t completed_tasks;
        size_t failed_tasks;
        size_t cancelled_tasks;
        std::chrono::milliseconds avg_execution_time;
        double tasks_per_second;
        size_t total_submitted_tasks;
    };
    TaskStatistics get_statistics() const;
    
    // 获取任务信息
    std::optional<TaskInfo> get_task_info(const std::string& task_id) const;
    
    // 获取待处理任务数
    size_t get_pending_task_count() const;
    
    // 获取运行中任务数
    size_t get_running_task_count() const;
    
    // 清空待处理任务
    void clear_pending_tasks();
    
    // 等待所有任务完成
    void wait_for_all_tasks();

private:
    class Impl;
    std::unique_ptr<Impl> pimpl_;
};

// 高性能线程池
class HighPerformanceThreadPool {
public:
    HighPerformanceThreadPool(size_t thread_count = std::thread::hardware_concurrency());
    ~HighPerformanceThreadPool();
    
    // 提交任务
    template<typename F, typename... Args>
    auto enqueue(F&& f, Args&&... args) -> std::future<typename std::result_of<F(Args...)>::type>;
    
    // 批量提交任务
    template<typename F>
    std::vector<std::future<typename std::result_of<F()>::type>> enqueue_batch(
        const std::vector<F>& tasks
    );
    
    // 动态调整线程数
    void resize(size_t new_size);
    
    // 获取当前线程数
    size_t size() const;
    
    // 获取活跃线程数
    size_t active_threads() const;
    
    // 获取队列中的任务数
    size_t queued_tasks() const;
    
    // 停止线程池
    void stop();
    
    // 等待所有任务完成并停止
    void stop_and_wait();

private:
    class Impl;
    std::unique_ptr<Impl> pimpl_;
};

// 工作窃取式任务队列
class WorkStealingTaskQueue {
public:
    WorkStealingTaskQueue(size_t num_workers = std::thread::hardware_concurrency());
    ~WorkStealingTaskQueue();
    
    // 提交任务到指定工作线程
    template<typename F>
    auto submit_to_thread(size_t thread_id, F&& f) -> std::future<typename std::result_of<F()>::type>;
    
    // 提交任务（自动分配）
    template<typename F>
    auto submit(F&& f) -> std::future<typename std::result_of<F()>::type>;
    
    // 启动工作线程
    void start();
    
    // 停止所有工作线程
    void stop();
    
    // 获取负载均衡信息
    struct LoadBalanceInfo {
        std::vector<size_t> queue_sizes;
        std::vector<size_t> completed_tasks;
        std::vector<double> utilization_rates;
        size_t total_steals;
    };
    LoadBalanceInfo get_load_balance_info() const;

private:
    class Impl;
    std::unique_ptr<Impl> pimpl_;
};

// 并发限制器
class ConcurrencyLimiter {
public:
    ConcurrencyLimiter(size_t max_concurrent_tasks);
    ~ConcurrencyLimiter();
    
    // 尝试获取执行许可
    bool try_acquire();
    
    // 阻塞获取执行许可
    void acquire();
    
    // 带超时获取执行许可
    bool acquire_for(std::chrono::milliseconds timeout);
    
    // 释放执行许可
    void release();
    
    // 获取当前并发数
    size_t current_concurrency() const;
    
    // 获取最大并发数
    size_t max_concurrency() const;
    
    // 设置最大并发数
    void set_max_concurrency(size_t max_concurrent);
    
    // RAII许可管理器
    class ScopedPermit {
    public:
        ScopedPermit(ConcurrencyLimiter& limiter);
        ~ScopedPermit();
        
        bool is_acquired() const;
        
    private:
        ConcurrencyLimiter& limiter_;
        bool acquired_;
    };

private:
    class Impl;
    std::unique_ptr<Impl> pimpl_;
};

// 异步执行器
class AsyncExecutor {
public:
    AsyncExecutor();
    ~AsyncExecutor();
    
    // 异步执行函数
    template<typename F, typename... Args>
    auto async(F&& f, Args&&... args) -> std::future<typename std::result_of<F(Args...)>::type>;
    
    // 异步执行带超时
    template<typename F, typename... Args>
    auto async_with_timeout(std::chrono::milliseconds timeout, F&& f, Args&&... args)
        -> std::future<std::optional<typename std::result_of<F(Args...)>::type>>;
    
    // 并行执行多个任务
    template<typename F>
    auto parallel_for_each(const std::vector<F>& tasks)
        -> std::vector<std::future<typename std::result_of<F()>::type>>;
    
    // 等待任意一个任务完成
    template<typename T>
    std::pair<size_t, T> wait_for_any(std::vector<std::future<T>>& futures);
    
    // 等待所有任务完成
    template<typename T>
    std::vector<T> wait_for_all(std::vector<std::future<T>>& futures);
    
    // 设置默认超时时间
    void set_default_timeout(std::chrono::milliseconds timeout);
    
    // 获取执行统计
    struct ExecutionStats {
        size_t total_executions;
        size_t successful_executions;
        size_t failed_executions;
        size_t timeout_executions;
        std::chrono::milliseconds avg_execution_time;
    };
    ExecutionStats get_execution_stats() const;

private:
    class Impl;
    std::unique_ptr<Impl> pimpl_;
};

// 流水线处理器
template<typename InputType, typename OutputType>
class PipelineProcessor {
public:
    using ProcessFunction = std::function<OutputType(const InputType&)>;
    using ErrorHandler = std::function<void(const std::exception&, const InputType&)>;
    
    PipelineProcessor(size_t buffer_size = 1000, size_t worker_threads = 4);
    ~PipelineProcessor();
    
    // 设置处理函数
    void set_process_function(ProcessFunction func);
    
    // 设置错误处理函数
    void set_error_handler(ErrorHandler handler);
    
    // 添加输入数据
    bool add_input(const InputType& input);
    bool add_input(InputType&& input);
    
    // 批量添加输入数据
    size_t add_input_batch(const std::vector<InputType>& inputs);
    
    // 获取处理结果
    std::optional<OutputType> get_result();
    
    // 批量获取处理结果
    std::vector<OutputType> get_results(size_t max_count);
    
    // 启动流水线
    void start();
    
    // 停止流水线
    void stop();
    
    // 等待处理完成
    void wait_for_completion();
    
    // 获取处理统计
    struct PipelineStats {
        size_t input_count;
        size_t processed_count;
        size_t output_count;
        size_t error_count;
        size_t queue_size;
        double throughput_per_second;
    };
    PipelineStats get_stats() const;

private:
    class Impl;
    std::unique_ptr<Impl> pimpl_;
};

// 任务调度策略
namespace scheduling_policies {
    // FIFO调度策略
    class FIFOScheduler {
    public:
        template<typename Task>
        bool should_execute_first(const Task& a, const Task& b) const;
    };
    
    // 优先级调度策略
    class PriorityScheduler {
    public:
        template<typename Task>
        bool should_execute_first(const Task& a, const Task& b) const;
    };
    
    // 最短作业优先调度策略
    class SJFScheduler {
    public:
        template<typename Task>
        bool should_execute_first(const Task& a, const Task& b) const;
    };
    
    // 公平调度策略
    class FairScheduler {
    public:
        template<typename Task>
        bool should_execute_first(const Task& a, const Task& b) const;
    };
}

// 并发性能优化配置
struct ConcurrencyConfig {
    size_t max_threads = std::thread::hardware_concurrency();
    size_t queue_capacity = 10000;
    bool enable_work_stealing = true;
    bool enable_thread_affinity = false;
    std::chrono::milliseconds task_timeout{30000};
    size_t max_retries = 3;
    bool enable_priority_inheritance = true;
    double load_balance_threshold = 0.8;
};

} // namespace ai_assistant