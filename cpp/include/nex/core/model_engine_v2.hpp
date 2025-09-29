#pragma once

#include "async_types.hpp"
#include "inference_types.hpp"
#include "../concepts/core_concepts.hpp"
#include <vector>
#include <memory>
#include <string>
#include <chrono>
#include <unordered_map>
#include <functional>

namespace hushell::core::inference {

    /**
     * @brief 模型配置结构体
     */
    struct ModelConfig {
        std::string model_id;
        std::string model_path;
        std::string model_type;  // "local", "cloud", "hybrid"
        
        // 推理参数
        int max_tokens = 1024;
        float temperature = 0.7f;
        float top_p = 0.9f;
        int top_k = 50;
        bool use_gpu = true;
        
        // 性能参数
        int batch_size = 1;
        int max_concurrent_requests = 10;
        std::chrono::milliseconds timeout = std::chrono::milliseconds(30000);
        
        // 缓存配置
        bool enable_cache = true;
        size_t cache_size = 1000;
        
        // 平台特定配置
        std::unordered_map<std::string, std::string> platform_options;
    };

    /**
     * @brief 推理请求结构体
     */
    struct InferenceRequest {
        std::string request_id;
        std::string model_id;
        std::string input;
        std::string system_prompt = "";
        
        // 推理参数（可覆盖模型默认配置）
        std::optional<int> max_tokens;
        std::optional<float> temperature;
        std::optional<float> top_p;
        std::optional<int> top_k;
        
        // 流式输出配置
        bool stream = false;
        std::function<void(const std::string&)> stream_callback;
        
        // 元数据
        std::unordered_map<std::string, std::string> metadata;
        std::chrono::steady_clock::time_point created_at = std::chrono::steady_clock::now();
    };

    /**
     * @brief 推理结果结构体
     */
    struct InferenceResult {
        std::string request_id;
        std::string model_id;
        std::string output;
        bool success = false;
        std::string error_message;
        
        // 性能指标
        std::chrono::milliseconds inference_time{0};
        std::chrono::milliseconds queue_time{0};
        std::chrono::milliseconds total_time{0};
        
        // token统计
        int input_tokens = 0;
        int output_tokens = 0;
        int total_tokens = 0;
        
        // 质量指标
        float confidence_score = 0.0f;
        std::vector<float> token_probabilities;
        
        // 元数据
        std::unordered_map<std::string, std::string> metadata;
        std::chrono::steady_clock::time_point completed_at = std::chrono::steady_clock::now();
    };

    /**
     * @brief 批量推理请求
     */
    struct BatchInferenceRequest {
        std::string batch_id;
        std::vector<InferenceRequest> requests;
        bool parallel_execution = true;
        std::chrono::milliseconds timeout = std::chrono::milliseconds(60000);
    };

    /**
     * @brief 批量推理结果
     */
    struct BatchInferenceResult {
        std::string batch_id;
        std::vector<InferenceResult> results;
        bool all_success = false;
        std::chrono::milliseconds total_time{0};
        
        // 批量统计
        int success_count = 0;
        int error_count = 0;
        double average_inference_time = 0.0;
    };

    /**
     * @brief 性能指标结构体
     */
    struct PerformanceMetrics {
        // 吞吐量指标
        double requests_per_second = 0.0;
        double tokens_per_second = 0.0;
        
        // 延迟指标
        std::chrono::milliseconds avg_latency{0};
        std::chrono::milliseconds p50_latency{0};
        std::chrono::milliseconds p95_latency{0};
        std::chrono::milliseconds p99_latency{0};
        
        // 资源使用
        double cpu_usage = 0.0;
        double memory_usage_mb = 0.0;
        double gpu_usage = 0.0;
        double gpu_memory_usage_mb = 0.0;
        
        // 队列统计
        int pending_requests = 0;
        int active_requests = 0;
        int completed_requests = 0;
        int failed_requests = 0;
        
        // 缓存统计
        double cache_hit_rate = 0.0;
        int cache_entries = 0;
        
        std::chrono::steady_clock::time_point timestamp = std::chrono::steady_clock::now();
    };

    /**
     * @brief 模型引擎接口 - 基于现代C++20协程的异步推理引擎
     */
    class IModelEngine {
    public:
        virtual ~IModelEngine() = default;

        // ========== 生命周期管理 ==========
        
        /**
         * @brief 初始化引擎
         */
        virtual Task<Result<void>> initialize() = 0;
        
        /**
         * @brief 关闭引擎
         */
        virtual Task<Result<void>> shutdown() = 0;
        
        /**
         * @brief 检查引擎状态
         */
        virtual bool is_initialized() const = 0;

        // ========== 模型管理 ==========
        
        /**
         * @brief 加载模型（异步）
         */
        virtual Task<Result<void>> load_model_async(const ModelConfig& config) = 0;
        
        /**
         * @brief 卸载模型（异步）
         */
        virtual Task<Result<void>> unload_model_async(const std::string& model_id) = 0;
        
        /**
         * @brief 重新加载模型（异步）
         */
        virtual Task<Result<void>> reload_model_async(const std::string& model_id) = 0;
        
        /**
         * @brief 获取已加载的模型列表
         */
        virtual std::vector<std::string> get_loaded_models() const = 0;
        
        /**
         * @brief 检查模型是否已加载
         */
        virtual bool is_model_loaded(const std::string& model_id) const = 0;
        
        /**
         * @brief 获取模型配置
         */
        virtual std::optional<ModelConfig> get_model_config(const std::string& model_id) const = 0;

        // ========== 推理接口 ==========
        
        /**
         * @brief 单次异步推理
         */
        virtual Task<Result<InferenceResult>> infer_async(const InferenceRequest& request) = 0;
        
        /**
         * @brief 批量异步推理
         */
        virtual Task<Result<BatchInferenceResult>> batch_infer_async(const BatchInferenceRequest& request) = 0;
        
        /**
         * @brief 流式推理（生成器模式）
         */
        virtual Task<Result<void>> stream_infer_async(
            const InferenceRequest& request,
            std::function<void(const std::string&)> callback
        ) = 0;

        // ========== 性能监控 ==========
        
        /**
         * @brief 获取性能指标
         */
        virtual PerformanceMetrics get_performance_metrics() const = 0;
        
        /**
         * @brief 重置性能指标
         */
        virtual void reset_performance_metrics() = 0;
        
        /**
         * @brief 获取引擎健康状态
         */
        virtual bool is_healthy() const = 0;

        // ========== 配置管理 ==========
        
        /**
         * @brief 更新全局配置
         */
        virtual Result<void> update_global_config(const std::unordered_map<std::string, std::string>& config) = 0;
        
        /**
         * @brief 获取全局配置
         */
        virtual std::unordered_map<std::string, std::string> get_global_config() const = 0;

        // ========== 缓存管理 ==========
        
        /**
         * @brief 清空推理缓存
         */
        virtual void clear_inference_cache() = 0;
        
        /**
         * @brief 预热模型（加载到GPU/内存）
         */
        virtual Task<Result<void>> warmup_model_async(const std::string& model_id) = 0;
    };

    /**
     * @brief 高性能模型引擎实现
     */
    class ModelEngine : public IModelEngine {
    public:
        explicit ModelEngine();
        virtual ~ModelEngine();

        // 禁用拷贝和移动
        ModelEngine(const ModelEngine&) = delete;
        ModelEngine& operator=(const ModelEngine&) = delete;
        ModelEngine(ModelEngine&&) = delete;
        ModelEngine& operator=(ModelEngine&&) = delete;

        // 实现IModelEngine接口
        Task<Result<void>> initialize() override;
        Task<Result<void>> shutdown() override;
        bool is_initialized() const override;

        Task<Result<void>> load_model_async(const ModelConfig& config) override;
        Task<Result<void>> unload_model_async(const std::string& model_id) override;
        Task<Result<void>> reload_model_async(const std::string& model_id) override;
        std::vector<std::string> get_loaded_models() const override;
        bool is_model_loaded(const std::string& model_id) const override;
        std::optional<ModelConfig> get_model_config(const std::string& model_id) const override;

        Task<Result<InferenceResult>> infer_async(const InferenceRequest& request) override;
        Task<Result<BatchInferenceResult>> batch_infer_async(const BatchInferenceRequest& request) override;
        Task<Result<void>> stream_infer_async(
            const InferenceRequest& request,
            std::function<void(const std::string&)> callback
        ) override;

        PerformanceMetrics get_performance_metrics() const override;
        void reset_performance_metrics() override;
        bool is_healthy() const override;

        Result<void> update_global_config(const std::unordered_map<std::string, std::string>& config) override;
        std::unordered_map<std::string, std::string> get_global_config() const override;

        void clear_inference_cache() override;
        Task<Result<void>> warmup_model_async(const std::string& model_id) override;

    private:
        class Impl;
        std::unique_ptr<Impl> pimpl_;
    };

    /**
     * @brief 模型引擎工厂
     */
    class ModelEngineFactory {
    public:
        /**
         * @brief 创建默认模型引擎
         */
        static std::unique_ptr<IModelEngine> create_default_engine();
        
        /**
         * @brief 创建带配置的模型引擎
         */
        static std::unique_ptr<IModelEngine> create_engine(const std::unordered_map<std::string, std::string>& config);
        
        /**
         * @brief 创建平台优化的模型引擎
         */
        static std::unique_ptr<IModelEngine> create_platform_optimized_engine();
    };

} // namespace hushell::core::inference