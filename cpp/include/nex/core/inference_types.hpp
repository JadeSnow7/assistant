#pragma once

#include "nex/concepts/core_concepts.hpp"
#include <coroutine>
#include <string>
#include <vector>
#include <memory>
#include <chrono>
#include <optional>
#include <map>

namespace nex::core::inference {

    /**
     * @brief 推理请求结构
     */
    struct InferenceRequest {
        std::string model_id;
        std::string input;
        int max_tokens = 1024;
        float temperature = 0.7f;
        float top_p = 0.9f;
        std::vector<std::string> stop_sequences;
        std::map<std::string, std::string> metadata;
        std::chrono::milliseconds timeout{30000};
        
        // 流式推理支持
        bool streaming = false;
        std::function<void(const std::string&)> stream_callback;
    };

    /**
     * @brief 推理结果结构
     */
    struct InferenceResult {
        std::string output;
        bool success = false;
        std::string error_message;
        std::chrono::milliseconds inference_time_ms{0};
        
        // 推理统计信息
        int tokens_generated = 0;
        int input_tokens = 0;
        double tokens_per_second = 0.0;
        
        // 模型信息
        std::string model_used;
        std::string provider_name;
        
        // 置信度和其他元数据
        std::optional<float> confidence;
        std::map<std::string, std::string> metadata;
    };

    /**
     * @brief 模型信息结构
     */
    struct ModelInfo {
        std::string id;
        std::string name;
        std::string description;
        std::string version;
        std::string provider;
        
        // 模型能力
        int max_context_length = 4096;
        int max_output_tokens = 1024;
        std::vector<std::string> supported_tasks;
        
        // 资源需求
        size_t memory_requirement_mb = 0;
        bool requires_gpu = false;
        std::string compute_type; // "cpu", "cuda", "opencl"
        
        // 性能指标
        double avg_tokens_per_second = 0.0;
        std::chrono::milliseconds avg_load_time_ms{0};
    };

    /**
     * @brief C++20协程返回类型 - 异步推理结果
     */
    template<typename T = InferenceResult>
    struct InferenceTask {
        struct promise_type {
            T value;
            std::exception_ptr exception;

            InferenceTask get_return_object() {
                return InferenceTask{std::coroutine_handle<promise_type>::from_promise(*this)};
            }

            std::suspend_never initial_suspend() { return {}; }
            std::suspend_never final_suspend() noexcept { return {}; }

            void return_value(T val) {
                value = std::move(val);
            }

            void unhandled_exception() {
                exception = std::current_exception();
            }
        };

        std::coroutine_handle<promise_type> coro;

        InferenceTask(std::coroutine_handle<promise_type> h) : coro(h) {}
        
        ~InferenceTask() {
            if (coro) coro.destroy();
        }

        // 移动语义
        InferenceTask(InferenceTask&& other) noexcept : coro(std::exchange(other.coro, {})) {}
        InferenceTask& operator=(InferenceTask&& other) noexcept {
            if (this != &other) {
                if (coro) coro.destroy();
                coro = std::exchange(other.coro, {});
            }
            return *this;
        }

        // 禁用拷贝
        InferenceTask(const InferenceTask&) = delete;
        InferenceTask& operator=(const InferenceTask&) = delete;

        T get() {
            if (coro.promise().exception) {
                std::rethrow_exception(coro.promise().exception);
            }
            return std::move(coro.promise().value);
        }

        bool ready() const {
            return coro && coro.done();
        }
    };

    /**
     * @brief 流式推理协程支持
     */
    template<typename T = std::string>
    struct StreamingInferenceTask {
        struct promise_type {
            std::vector<T> values;
            std::exception_ptr exception;
            bool finished = false;

            StreamingInferenceTask get_return_object() {
                return StreamingInferenceTask{std::coroutine_handle<promise_type>::from_promise(*this)};
            }

            std::suspend_never initial_suspend() { return {}; }
            std::suspend_never final_suspend() noexcept { 
                finished = true;
                return {}; 
            }

            // 协程yield支持
            std::suspend_always yield_value(T val) {
                values.push_back(std::move(val));
                return {};
            }

            void return_void() {
                finished = true;
            }

            void unhandled_exception() {
                exception = std::current_exception();
            }
        };

        std::coroutine_handle<promise_type> coro;

        StreamingInferenceTask(std::coroutine_handle<promise_type> h) : coro(h) {}
        
        ~StreamingInferenceTask() {
            if (coro) coro.destroy();
        }

        // 移动语义
        StreamingInferenceTask(StreamingInferenceTask&& other) noexcept 
            : coro(std::exchange(other.coro, {})) {}
        StreamingInferenceTask& operator=(StreamingInferenceTask&& other) noexcept {
            if (this != &other) {
                if (coro) coro.destroy();
                coro = std::exchange(other.coro, {});
            }
            return *this;
        }

        // 禁用拷贝
        StreamingInferenceTask(const StreamingInferenceTask&) = delete;
        StreamingInferenceTask& operator=(const StreamingInferenceTask&) = delete;

        // 迭代器支持
        class iterator {
        private:
            StreamingInferenceTask* task_;
            size_t index_ = 0;

        public:
            iterator(StreamingInferenceTask* task, size_t index) : task_(task), index_(index) {}

            T& operator*() {
                return task_->coro.promise().values[index_];
            }

            iterator& operator++() {
                ++index_;
                return *this;
            }

            bool operator!=(const iterator& other) const {
                return index_ != other.index_ || task_ != other.task_;
            }
        };

        iterator begin() {
            return iterator(this, 0);
        }

        iterator end() {
            return iterator(this, coro.promise().values.size());
        }

        bool finished() const {
            return coro && coro.promise().finished;
        }

        std::vector<T> get_all() {
            if (coro.promise().exception) {
                std::rethrow_exception(coro.promise().exception);
            }
            return std::move(coro.promise().values);
        }
    };

} // namespace nex::core::inference