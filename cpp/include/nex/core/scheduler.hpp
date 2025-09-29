#pragma once

#include "async_types.hpp"
#include "../platform_config.h"
#include <thread>
#include <vector>
#include <queue>
#include <functional>
#include <mutex>
#include <condition_variable>
#include <atomic>
#include <future>
#include <chrono>
#include <memory>

namespace hushell::core::scheduler {

    /**
     * @brief 负载均衡信息
     */
    struct LoadBalanceInfo {
        size_t total_threads = 0;
        size_t active_threads = 0;
        size_t pending_tasks = 0;
        size_t completed_tasks = 0;
        double cpu_usage = 0.0;
        std::chrono::milliseconds avg_task_duration{0};
    };

    /**
     * @brief 任务优先级
     */
    enum class TaskPriority {
        LOW = 0,
        NORMAL = 1,
        HIGH = 2,
        CRITICAL = 3
    };

    /**
     * @brief 任务元数据
     */
    struct TaskMetadata {
        std::string task_id;
        TaskPriority priority = TaskPriority::NORMAL;
        std::chrono::steady_clock::time_point created_at = std::chrono::steady_clock::now();
        std::chrono::steady_clock::time_point started_at;
        std::chrono::steady_clock::time_point completed_at;
        std::chrono::milliseconds timeout = std::chrono::milliseconds::max();
    };

    /**
     * @brief 工作窃取线程池 - 高性能任务调度
     */
    class WorkStealingPool {
    public:
        /**
         * @brief 构造函数
         * @param thread_count 线程数量，0表示使用CPU核心数
         */
        explicit WorkStealingPool(size_t thread_count = 0);

        /**
         * @brief 析构函数
         */
        ~WorkStealingPool();

        /**
         * @brief 提交任务
         */
        template<typename F, typename... Args>
        auto submit_task(F&& func, Args&&... args) -> std::future<std::invoke_result_t<F, Args...>> {
            using ReturnType = std::invoke_result_t<F, Args...>;
            
            auto task = std::make_shared<std::packaged_task<ReturnType()>>(
                std::bind(std::forward<F>(func), std::forward<Args>(args)...)
            );
            
            auto future = task->get_future();
            
            {
                std::lock_guard<std::mutex> lock(queue_mutex_);
                if (shutdown_) {
                    throw std::runtime_error("ThreadPool is shutting down");
                }
                tasks_.emplace([task]() { (*task)(); });
            }
            
            condition_.notify_one();
            return future;
        }

        /**
         * @brief 提交带优先级的任务
         */
        template<typename F, typename... Args>
        auto submit_priority_task(TaskPriority priority, F&& func, Args&&... args) 
            -> std::future<std::invoke_result_t<F, Args...>> {
            using ReturnType = std::invoke_result_t<F, Args...>;
            
            auto task = std::make_shared<std::packaged_task<ReturnType()>>(
                std::bind(std::forward<F>(func), std::forward<Args>(args)...)
            );
            
            auto future = task->get_future();
            
            {
                std::lock_guard<std::mutex> lock(queue_mutex_);
                if (shutdown_) {
                    throw std::runtime_error("ThreadPool is shutting down");
                }
                priority_tasks_.emplace(priority, [task]() { (*task)(); });
            }
            
            condition_.notify_one();
            return future;
        }

        /**
         * @brief 设置线程数量
         */
        void set_thread_count(size_t count);

        /**
         * @brief 获取负载信息
         */
        LoadBalanceInfo get_load_info() const;

        /**
         * @brief 等待所有任务完成
         */
        void wait_for_all_tasks();

        /**
         * @brief 关闭线程池
         */
        void shutdown();

    private:
        struct PriorityTask {
            TaskPriority priority;
            std::function<void()> task;
            
            bool operator<(const PriorityTask& other) const {
                return priority < other.priority;  // 优先级队列是大顶堆
            }
        };

        void worker_thread(size_t thread_id);
        bool try_steal_task(std::function<void()>& task);

        std::vector<std::thread> workers_;
        std::queue<std::function<void()>> tasks_;
        std::priority_queue<PriorityTask> priority_tasks_;
        
        mutable std::mutex queue_mutex_;
        std::condition_variable condition_;
        std::atomic<bool> shutdown_{false};
        
        std::atomic<size_t> active_threads_{0};
        std::atomic<size_t> pending_tasks_{0};
        std::atomic<size_t> completed_tasks_{0};
    };

    /**
     * @brief 并发限制器 - 控制并发执行数量
     */
    class ConcurrencyLimiter {
    public:
        /**
         * @brief 构造函数
         * @param max_permits 最大并发数
         */
        explicit ConcurrencyLimiter(size_t max_permits);

        /**
         * @brief 异步获取执行许可
         */
        Task<void> acquire_permit();

        /**
         * @brief 释放执行许可
         */
        void release_permit();

        /**
         * @brief 获取当前许可数
         */
        size_t current_permits() const;

        /**
         * @brief 获取可用许可数
         */
        size_t available_permits() const;

        /**
         * @brief 获取等待队列长度
         */
        size_t waiting_count() const;

    private:
        const size_t max_permits_;
        std::atomic<size_t> current_permits_{0};
        mutable std::mutex mutex_;
        std::condition_variable condition_;
        std::queue<std::promise<void>> waiting_queue_;
    };

    /**
     * @brief 异步调度器 - 协程任务调度器
     */
    class AsyncScheduler {
    public:
        /**
         * @brief 构造函数
         */
        explicit AsyncScheduler(size_t thread_count = 0);

        /**
         * @brief 析构函数
         */
        ~AsyncScheduler();

        /**
         * @brief 调度协程任务
         */
        template<typename F>
        Task<std::invoke_result_t<F>> schedule(F&& func) {
            using ReturnType = std::invoke_result_t<F>;
            
            if constexpr (std::is_void_v<ReturnType>) {
                co_await schedule_impl([func = std::forward<F>(func)]() {
                    func();
                    return 0;  // 占位返回值
                });
            } else {
                co_return co_await schedule_impl(std::forward<F>(func));
            }
        }

        /**
         * @brief 调度带超时的协程任务
         */
        template<typename F>
        Task<std::optional<std::invoke_result_t<F>>> schedule_with_timeout(
            F&& func, 
            std::chrono::milliseconds timeout
        ) {
            auto task = schedule(std::forward<F>(func));
            co_return co_await task.timeout(timeout);
        }

        /**
         * @brief 并行执行多个任务
         */
        template<typename... Tasks>
        Task<std::tuple<typename Tasks::value_type...>> parallel(Tasks&&... tasks) {
            return when_all(std::forward<Tasks>(tasks)...);
        }

        /**
         * @brief 获取工作窃取池
         */
        WorkStealingPool& get_thread_pool();

        /**
         * @brief 获取并发限制器
         */
        ConcurrencyLimiter& get_concurrency_limiter();

        /**
         * @brief 设置全局并发限制
         */
        void set_global_concurrency_limit(size_t limit);

        /**
         * @brief 获取调度器统计信息
         */
        LoadBalanceInfo get_scheduler_stats() const;

        /**
         * @brief 关闭调度器
         */
        void shutdown();

    private:
        template<typename F>
        Task<std::invoke_result_t<F>> schedule_impl(F&& func) {
            using ReturnType = std::invoke_result_t<F>;
            
            std::promise<ReturnType> promise;
            auto future = promise.get_future();
            
            thread_pool_->submit_task([func = std::forward<F>(func), promise = std::move(promise)]() mutable {
                try {
                    if constexpr (std::is_void_v<ReturnType>) {
                        func();
                        promise.set_value();
                    } else {
                        promise.set_value(func());
                    }
                } catch (...) {
                    promise.set_exception(std::current_exception());
                }
            });
            
            // 等待任务完成
            while (future.wait_for(std::chrono::milliseconds(1)) != std::future_status::ready) {
                co_await yield();
            }
            
            if constexpr (std::is_void_v<ReturnType>) {
                future.get();  // 可能抛出异常
                co_return;
            } else {
                co_return future.get();
            }
        }

        std::unique_ptr<WorkStealingPool> thread_pool_;
        std::unique_ptr<ConcurrencyLimiter> concurrency_limiter_;
        std::atomic<bool> shutdown_{false};
    };

    /**
     * @brief 全局调度器管理器
     */
    class SchedulerManager {
    public:
        /**
         * @brief 获取单例实例
         */
        static SchedulerManager& instance();

        /**
         * @brief 初始化调度器
         */
        Result<void> initialize(const std::unordered_map<std::string, std::string>& config = {});

        /**
         * @brief 获取默认调度器
         */
        AsyncScheduler& get_default_scheduler();

        /**
         * @brief 创建专用调度器
         */
        std::unique_ptr<AsyncScheduler> create_dedicated_scheduler(const std::string& name, size_t thread_count = 0);

        /**
         * @brief 关闭所有调度器
         */
        void shutdown_all();

        /**
         * @brief 获取全局统计信息
         */
        LoadBalanceInfo get_global_stats() const;

    private:
        SchedulerManager() = default;
        ~SchedulerManager() = default;

        // 禁用拷贝和移动
        SchedulerManager(const SchedulerManager&) = delete;
        SchedulerManager& operator=(const SchedulerManager&) = delete;

        std::unique_ptr<AsyncScheduler> default_scheduler_;
        mutable std::mutex mutex_;
        std::atomic<bool> initialized_{false};
    };

} // namespace hushell::core::scheduler