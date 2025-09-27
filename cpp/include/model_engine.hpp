#pragma once

#include <memory>
#include <string>
#include <vector>
#include <functional>
#include <future>

namespace ai_assistant {

// 模型类型枚举
enum class ModelType {
    LOCAL_SMALL,    // 本地小模型
    CLOUD_LARGE,    // 云端大模型
    AUTO_SELECT     // 自动选择
};

// 推理请求结构
struct InferenceRequest {
    std::string prompt;
    ModelType model_type = ModelType::AUTO_SELECT;
    int max_tokens = 1024;
    float temperature = 0.7f;
    bool stream = false;
    std::string session_id;
};

// 推理响应结构
struct InferenceResponse {
    std::string text;
    bool finished = false;
    float confidence = 0.0f;
    ModelType used_model;
    int token_count = 0;
    double latency_ms = 0.0;
};

// 流式回调类型
using StreamCallback = std::function<void(const InferenceResponse&)>;

/**
 * 模型推理引擎
 * 封装llama.cpp和云端API调用
 */
class ModelEngine {
public:
    ModelEngine();
    ~ModelEngine();

    // 初始化引擎
    bool initialize(const std::string& config_path);
    
    // 同步推理
    InferenceResponse inference(const InferenceRequest& request);
    
    // 异步推理
    std::future<InferenceResponse> inference_async(const InferenceRequest& request);
    
    // 流式推理
    void inference_stream(const InferenceRequest& request, StreamCallback callback);
    
    // 加载本地模型
    bool load_local_model(const std::string& model_path);
    
    // 设置云端API配置
    void set_cloud_config(const std::string& api_key, const std::string& endpoint);
    
    // 获取模型信息
    std::vector<std::string> get_available_models() const;
    
    // 健康检查
    bool is_healthy() const;

private:
    class Impl;
    std::unique_ptr<Impl> pimpl_;
};

} // namespace ai_assistant