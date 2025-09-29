#pragma once

#include <coroutine>
#include <future>
#include <memory>
#include <string>
#include <chrono>
#include <optional>
#include <variant>
#include <functional>
#include <exception>

namespace hushell::core {

    /**
     * @brief 协程任务类型 - 基于C++20协程的异步编程模型
     * @tparam T 任务返回值类型
     */
    template<typename T>
    class Task {
    public:
        /**
         * @brief 协程promise类型
         */
        struct promise_type {
            std::optional<T> result;
            std::exception_ptr exception;
            std::coroutine_handle<> continuation;

            Task get_return_object() {
                return Task{std::coroutine_handle<promise_type>::from_promise(*this)};
            }

            std::suspend_never initial_suspend() noexcept { return {}; }
            
            std::suspend_always final_suspend() noexcept { 
                if (continuation) {
                    continuation.resume();
                }
                return {}; 
            }

            void return_value(T value) {
                result = std::move(value);
            }

            void unhandled_exception() {
                exception = std::current_exception();
            }
        };

        /**
         * @brief 构造函数
         */
        explicit Task(std::coroutine_handle<promise_type> handle) 
            : handle_(handle) {}

        /**
         * @brief 移动构造
         */
        Task(Task&& other) noexcept : handle_(std::exchange(other.handle_, {})) {}
        
        /**
         * @brief 移动赋值
         */
        Task& operator=(Task&& other) noexcept {
            if (this != &other) {
                if (handle_) {
                    handle_.destroy();
                }
                handle_ = std::exchange(other.handle_, {});
            }
            return *this;
        }

        /**
         * @brief 禁用拷贝
         */
        Task(const Task&) = delete;
        Task& operator=(const Task&) = delete;

        /**
         * @brief 析构函数
         */
        ~Task() {
            if (handle_) {
                handle_.destroy();
            }
        }

        /**
         * @brief awaitable接口 - 检查是否就绪
         */
        bool await_ready() const noexcept {
            return handle_.done();
        }

        /**
         * @brief awaitable接口 - 挂起时调用
         */
        void await_suspend(std::coroutine_handle<> continuation) noexcept {
            handle_.promise().continuation = continuation;
        }

        /**
         * @brief awaitable接口 - 恢复时获取结果
         */
        T await_resume() {
            if (handle_.promise().exception) {
                std::rethrow_exception(handle_.promise().exception);
            }
            return std::move(*handle_.promise().result);
        }

        /**
         * @brief 检查任务是否完成
         */
        bool is_ready() const noexcept {
            return handle_.done();
        }

        /**
         * @brief 等待任务完成（阻塞）
         */
        T get() {
            while (!handle_.done()) {
                std::this_thread::sleep_for(std::chrono::microseconds(1));
            }
            return await_resume();
        }

        /**
         * @brief 链式操作 - then
         */
        template<typename F>
        auto then(F&& func) -> Task<std::invoke_result_t<F, T>> {
            using ResultType = std::invoke_result_t<F, T>;
            
            try {
                T result = co_await *this;
                if constexpr (std::is_void_v<ResultType>) {
                    func(result);
                    co_return;
                } else {
                    co_return func(result);
                }
            } catch (...) {
                throw;
            }
        }

        /**
         * @brief 超时控制
         */
        Task<std::optional<T>> timeout(std::chrono::milliseconds duration) {
            auto start = std::chrono::steady_clock::now();
            
            while (!handle_.done()) {
                auto now = std::chrono::steady_clock::now();
                if (now - start > duration) {
                    co_return std::nullopt;
                }
                co_await sleep_for(std::chrono::milliseconds(1));
            }
            
            co_return await_resume();
        }

    private:
        std::coroutine_handle<promise_type> handle_;
    };

    /**
     * @brief 错误代码枚举
     */
    enum class ErrorCode {
        SUCCESS = 0,
        INVALID_ARGUMENT = 1,
        RESOURCE_EXHAUSTED = 2, 
        INTERNAL_ERROR = 3,
        PLATFORM_ERROR = 4,
        NETWORK_ERROR = 5,
        TIMEOUT_ERROR = 6,
        MODEL_NOT_FOUND = 7,
        INFERENCE_FAILED = 8,
        GPU_ERROR = 9,
        MEMORY_ERROR = 10
    };

    /**
     * @brief 错误代码转字符串
     */
    inline std::string error_code_to_string(ErrorCode code) {
        switch (code) {
            case ErrorCode::SUCCESS: return "Success";
            case ErrorCode::INVALID_ARGUMENT: return "Invalid argument";
            case ErrorCode::RESOURCE_EXHAUSTED: return "Resource exhausted";
            case ErrorCode::INTERNAL_ERROR: return "Internal error";
            case ErrorCode::PLATFORM_ERROR: return "Platform error";
            case ErrorCode::NETWORK_ERROR: return "Network error";
            case ErrorCode::TIMEOUT_ERROR: return "Timeout error";
            case ErrorCode::MODEL_NOT_FOUND: return "Model not found";
            case ErrorCode::INFERENCE_FAILED: return "Inference failed";
            case ErrorCode::GPU_ERROR: return "GPU error";
            case ErrorCode::MEMORY_ERROR: return "Memory error";
            default: return "Unknown error";
        }
    }

    /**
     * @brief 结果包装器 - 基于Rust的Result模式
     */
    template<typename T>
    class Result {
    public:
        /**
         * @brief 成功结果构造
         */
        static Result<T> success(T value) {
            return Result{std::move(value), ErrorCode::SUCCESS, ""};
        }

        /**
         * @brief 错误结果构造
         */
        static Result<T> error(ErrorCode code, std::string message = "") {
            if (message.empty()) {
                message = error_code_to_string(code);
            }
            return Result{std::nullopt, code, std::move(message)};
        }

        /**
         * @brief 检查是否成功
         */
        bool is_success() const noexcept {
            return value_.has_value();
        }

        /**
         * @brief 检查是否失败
         */
        bool is_error() const noexcept {
            return !value_.has_value();
        }

        /**
         * @brief 获取值（成功时）
         */
        const T& value() const {
            if (!is_success()) {
                throw std::runtime_error("Attempted to access value of failed Result");
            }
            return *value_;
        }

        /**
         * @brief 获取值（成功时，移动版本）
         */
        T&& value() && {
            if (!is_success()) {
                throw std::runtime_error("Attempted to access value of failed Result");
            }
            return std::move(*value_);
        }

        /**
         * @brief 获取错误码
         */
        ErrorCode error_code() const noexcept {
            return error_code_;
        }

        /**
         * @brief 获取错误消息
         */
        const std::string& error_message() const noexcept {
            return error_message_;
        }

        /**
         * @brief 链式操作 - and_then (monadic bind)
         */
        template<typename F>
        auto and_then(F&& f) -> Result<std::invoke_result_t<F, T>> {
            using ReturnType = std::invoke_result_t<F, T>;
            
            if (is_error()) {
                return Result<ReturnType>::error(error_code_, error_message_);
            }
            
            if constexpr (std::is_same_v<ReturnType, void>) {
                f(value());
                return Result<void>::success();
            } else {
                return f(value());
            }
        }

        /**
         * @brief 错误处理 - or_else
         */
        template<typename F>
        Result<T> or_else(F&& f) {
            if (is_success()) {
                return *this;
            }
            return f(error_code_, error_message_);
        }

        /**
         * @brief 获取值或默认值
         */
        T value_or(T default_value) const {
            return is_success() ? value() : std::move(default_value);
        }

        /**
         * @brief 映射操作 - map
         */
        template<typename F>
        auto map(F&& f) -> Result<std::invoke_result_t<F, T>> {
            using ReturnType = std::invoke_result_t<F, T>;
            
            if (is_error()) {
                return Result<ReturnType>::error(error_code_, error_message_);
            }
            
            return Result<ReturnType>::success(f(value()));
        }

    private:
        Result(std::optional<T> value, ErrorCode code, std::string message)
            : value_(std::move(value)), error_code_(code), error_message_(std::move(message)) {}

        std::optional<T> value_;
        ErrorCode error_code_;
        std::string error_message_;
    };

    /**
     * @brief void特化版本
     */
    template<>
    class Result<void> {
    public:
        static Result<void> success() {
            return Result{true, ErrorCode::SUCCESS, ""};
        }

        static Result<void> error(ErrorCode code, std::string message = "") {
            if (message.empty()) {
                message = error_code_to_string(code);
            }
            return Result{false, code, std::move(message)};
        }

        bool is_success() const noexcept { return success_; }
        bool is_error() const noexcept { return !success_; }
        ErrorCode error_code() const noexcept { return error_code_; }
        const std::string& error_message() const noexcept { return error_message_; }

    private:
        Result(bool success, ErrorCode code, std::string message)
            : success_(success), error_code_(code), error_message_(std::move(message)) {}

        bool success_;
        ErrorCode error_code_;
        std::string error_message_;
    };

    /**
     * @brief 协程工具函数
     */
    
    /**
     * @brief 休眠指定时间
     */
    inline Task<void> sleep_for(std::chrono::milliseconds duration) {
        auto start = std::chrono::steady_clock::now();
        while (std::chrono::steady_clock::now() - start < duration) {
            co_await std::suspend_always{};
        }
    }

    /**
     * @brief 让出执行权
     */
    inline Task<void> yield() {
        co_await std::suspend_always{};
    }

    /**
     * @brief 等待所有任务完成 - when_all
     */
    template<typename... Tasks>
    Task<std::tuple<typename Tasks::value_type...>> when_all(Tasks&&... tasks) {
        std::tuple<typename Tasks::value_type...> results;
        
        // 这是一个简化实现，真实实现需要更复杂的协程调度
        auto run_task = [](auto& task, auto& result) -> Task<void> {
            result = co_await task;
        };
        
        // 启动所有任务
        (co_await run_task(tasks, std::get<sizeof...(Tasks) - 1 - sizeof...(tasks)>(results)), ...);
        
        co_return results;
    }

    /**
     * @brief 等待任意任务完成 - when_any
     */
    template<typename... Tasks>
    Task<std::variant<typename Tasks::value_type...>> when_any(Tasks&&... tasks) {
        // 简化实现 - 实际需要使用选择器模式
        // 这里只是展示接口设计
        co_return std::variant<typename Tasks::value_type...>{};
    }

} // namespace hushell::core