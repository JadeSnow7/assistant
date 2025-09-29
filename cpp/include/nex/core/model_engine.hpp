#pragma once

#include "nex/core/inference_types.hpp"
#include "nex/concepts/core_concepts.hpp"
#include <memory>
#include <unordered_map>
#include <vector>
#include <atomic>
#include <mutex>

namespace nex::core::inference {

    /**
     * @brief 模型提供商接口基类
     */
    class IModelProvider {
    public:
        virtual ~IModelProvider() = default;

        // 基本信息
        virtual std::string get_name() const = 0;
        virtual std::string get_version() const = 0;
        virtual bool is_available() const = 0;

        // 生命周期管理
        virtual bool initialize() = 0;
        virtual void shutdown() = 0;

        // 模型管理
        virtual std::vector<ModelInfo> get_supported_models() const = 0;
        virtual bool load_model(const std::string& model_id) = 0;
        virtual bool unload_model(const std::string& model_id) = 0;
        virtual bool is_model_loaded(const std::string& model_id) const = 0;
        virtual std::optional<ModelInfo> get_model_info(const std::string& model_id) const = 0;

        // 推理接口
        virtual InferenceTask<InferenceResult> inference_async(const InferenceRequest& request) = 0;
        virtual StreamingInferenceTask<std::string> streaming_inference_async(const InferenceRequest& request) = 0;

        // 同步接口（为了兼容性）
        virtual InferenceResult inference_sync(const InferenceRequest& request) = 0;

        // 批量推理
        virtual std::vector<InferenceResult> batch_inference(const std::vector<InferenceRequest>& requests) = 0;

        // 性能和统计
        virtual size_t get_memory_usage() const = 0;
        virtual double get_average_inference_time() const = 0;
        virtual size_t get_total_requests() const = 0;
    };

    /**
     * @brief 本地模型提供商（Ollama等）
     */
    class LocalModelProvider : public IModelProvider {
    public:
        explicit LocalModelProvider(const std::string& base_url = "http://localhost:11434");
        ~LocalModelProvider() override = default;

        // 基本信息
        std::string get_name() const override { return "LocalModelProvider"; }
        std::string get_version() const override { return "1.0.0"; }
        bool is_available() const override;

        // 生命周期管理
        bool initialize() override;
        void shutdown() override;

        // 模型管理
        std::vector<ModelInfo> get_supported_models() const override;
        bool load_model(const std::string& model_id) override;
        bool unload_model(const std::string& model_id) override;
        bool is_model_loaded(const std::string& model_id) const override;
        std::optional<ModelInfo> get_model_info(const std::string& model_id) const override;

        // 推理接口
        InferenceTask<InferenceResult> inference_async(const InferenceRequest& request) override;
        StreamingInferenceTask<std::string> streaming_inference_async(const InferenceRequest& request) override;
        InferenceResult inference_sync(const InferenceRequest& request) override;
        std::vector<InferenceResult> batch_inference(const std::vector<InferenceRequest>& requests) override;

        // 性能和统计
        size_t get_memory_usage() const override;
        double get_average_inference_time() const override;
        size_t get_total_requests() const override;

    private:
        std::string base_url_;
        std::atomic<bool> initialized_{false};
        std::unordered_map<std::string, ModelInfo> loaded_models_;
        mutable std::mutex models_mutex_;
        
        // 统计信息
        std::atomic<size_t> total_requests_{0};
        std::atomic<size_t> total_inference_time_ms_{0};
        
        // 私有方法
        bool check_ollama_connection() const;
        ModelInfo fetch_model_info(const std::string& model_id) const;
        InferenceResult perform_inference(const InferenceRequest& request);
    };

    /**
     * @brief 云端模型提供商（Gemini、OpenAI等）
     */
    class CloudModelProvider : public IModelProvider {
    public:
        explicit CloudModelProvider(
            const std::string& provider_name,
            const std::string& api_key,
            const std::string& base_url = ""
        );
        ~CloudModelProvider() override = default;

        // 基本信息
        std::string get_name() const override { return provider_name_; }
        std::string get_version() const override { return "1.0.0"; }
        bool is_available() const override;

        // 生命周期管理
        bool initialize() override;
        void shutdown() override;

        // 模型管理
        std::vector<ModelInfo> get_supported_models() const override;
        bool load_model(const std::string& model_id) override;
        bool unload_model(const std::string& model_id) override;
        bool is_model_loaded(const std::string& model_id) const override;
        std::optional<ModelInfo> get_model_info(const std::string& model_id) const override;

        // 推理接口
        InferenceTask<InferenceResult> inference_async(const InferenceRequest& request) override;
        StreamingInferenceTask<std::string> streaming_inference_async(const InferenceRequest& request) override;
        InferenceResult inference_sync(const InferenceRequest& request) override;
        std::vector<InferenceResult> batch_inference(const std::vector<InferenceRequest>& requests) override;

        // 性能和统计
        size_t get_memory_usage() const override { return 0; } // 云端不占用本地内存
        double get_average_inference_time() const override;
        size_t get_total_requests() const override;

    private:
        std::string provider_name_;
        std::string api_key_;
        std::string base_url_;
        std::atomic<bool> initialized_{false};
        std::unordered_map<std::string, ModelInfo> available_models_;
        mutable std::mutex models_mutex_;
        
        // 统计信息
        std::atomic<size_t> total_requests_{0};
        std::atomic<size_t> total_inference_time_ms_{0};
        
        // 私有方法
        bool check_api_connection() const;
        std::vector<ModelInfo> fetch_available_models() const;
        InferenceResult perform_cloud_inference(const InferenceRequest& request);
    };

    /**
     * @brief 模型引擎 - 管理多个模型提供商并提供统一接口
     */
    class ModelEngine {
    public:
        ModelEngine() = default;
        ~ModelEngine() = default;

        // 禁用拷贝，允许移动
        ModelEngine(const ModelEngine&) = delete;
        ModelEngine& operator=(const ModelEngine&) = delete;
        ModelEngine(ModelEngine&&) = default;
        ModelEngine& operator=(ModelEngine&&) = default;

        /**
         * @brief 注册模型提供商
         * @tparam T 提供商类型，必须满足ModelProvider概念
         * @param provider 提供商实例
         * @return bool 注册是否成功
         */
        template<concepts::ModelProvider T>
        bool register_provider(std::unique_ptr<T> provider) {
            std::lock_guard<std::mutex> lock(providers_mutex_);
            auto name = provider->get_name();
            
            if (providers_.find(name) != providers_.end()) {
                return false; // 提供商已存在
            }
            
            if (!provider->initialize()) {
                return false; // 初始化失败
            }
            
            providers_[name] = std::move(provider);
            return true;
        }

        /**
         * @brief 注销模型提供商
         * @param provider_name 提供商名称
         * @return bool 注销是否成功
         */
        bool unregister_provider(const std::string& provider_name);

        /**
         * @brief 获取所有可用的模型
         * @return std::vector<ModelInfo> 模型信息列表
         */
        std::vector<ModelInfo> get_available_models() const;

        /**
         * @brief 选择最佳提供商进行推理
         * @param request 推理请求
         * @return InferenceTask<InferenceResult> 异步推理任务
         */
        InferenceTask<InferenceResult> inference_async(const InferenceRequest& request);

        /**
         * @brief 流式推理
         * @param request 推理请求
         * @return StreamingInferenceTask<std::string> 流式推理任务
         */
        StreamingInferenceTask<std::string> streaming_inference_async(const InferenceRequest& request);

        /**
         * @brief 同步推理
         * @param request 推理请求
         * @return InferenceResult 推理结果
         */
        InferenceResult inference_sync(const InferenceRequest& request);

        /**
         * @brief 批量推理
         * @param requests 推理请求列表
         * @return std::vector<InferenceResult> 推理结果列表
         */
        std::vector<InferenceResult> batch_inference(const std::vector<InferenceRequest>& requests);

        /**
         * @brief 获取引擎统计信息
         * @return std::map<std::string, std::any> 统计信息
         */
        std::map<std::string, std::string> get_statistics() const;

        /**
         * @brief 设置智能路由策略
         * @param strategy 路由策略函数
         */
        void set_routing_strategy(
            std::function<std::string(const InferenceRequest&, const std::vector<std::string>&)> strategy
        );

    private:
        std::unordered_map<std::string, std::unique_ptr<IModelProvider>> providers_;
        mutable std::mutex providers_mutex_;
        
        // 智能路由
        std::function<std::string(const InferenceRequest&, const std::vector<std::string>&)> routing_strategy_;
        
        // 统计信息
        std::atomic<size_t> total_requests_{0};
        std::atomic<size_t> successful_requests_{0};
        std::atomic<size_t> failed_requests_{0};
        
        // 私有方法
        std::string select_best_provider(const InferenceRequest& request) const;
        IModelProvider* get_provider(const std::string& provider_name) const;
        std::string default_routing_strategy(
            const InferenceRequest& request, 
            const std::vector<std::string>& available_providers
        ) const;
    };

} // namespace nex::core::inference