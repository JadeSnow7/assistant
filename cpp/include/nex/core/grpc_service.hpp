#pragma once

#include "../core/async_types.hpp"
#include "../platform_config.h"

#ifdef HUSHELL_ENABLE_GRPC

#include <grpcpp/grpcpp.h>
#include <grpcpp/server.h>
#include <grpcpp/server_builder.h>
#include <grpcpp/server_context.h>
#include <grpcpp/security/server_credentials.h>
#include <memory>
#include <string>
#include <unordered_map>
#include <atomic>
#include <thread>

// Forward declarations for generated protobuf classes
namespace hushell::core {
    class InferenceRequest;
    class InferenceResult;
    class BatchInferenceRequest;
    class BatchInferenceResult;
    class StreamInferenceResponse;
    class LoadModelRequest;
    class LoadModelResponse;
    class UnloadModelRequest;
    class UnloadModelResponse;
    class ListModelsRequest;
    class ListModelsResponse;
    class SystemInfoRequest;
    class SystemInfoResponse;
    class MetricsRequest;
    class MetricsResponse;
    class ResourceRequest;
    class ResourceResponse;
    class LoadPluginRequest;
    class LoadPluginResponse;
    class UnloadPluginRequest;
    class UnloadPluginResponse;
    class ListPluginsRequest;
    class ListPluginsResponse;
    class PluginCallRequest;
    class PluginCallResponse;
}

namespace hushell::core::grpc {

    /**
     * @brief gRPC服务器配置
     */
    struct GrpcServerConfig {
        std::string listen_address = "0.0.0.0";
        int port = 50051;
        int max_concurrent_streams = 1000;
        int max_message_size_mb = 16;
        int keepalive_time_s = 300;
        int keepalive_timeout_s = 5;
        bool keepalive_permit_without_calls = true;
        bool use_ssl = false;
        std::string ssl_cert_path;
        std::string ssl_key_path;
        std::string ssl_ca_path;
        int thread_pool_size = 0; // 0 = auto detect
        
        // 性能调优参数
        int channel_args_max_receive_message_length = -1;
        int channel_args_max_send_message_length = -1;
        bool enable_reflection = false;
        bool enable_health_service = true;
    };

    /**
     * @brief gRPC客户端配置
     */
    struct GrpcClientConfig {
        std::string server_address = "localhost:50051";
        int max_message_size_mb = 16;
        int keepalive_time_s = 300;
        int keepalive_timeout_s = 5;
        bool keepalive_permit_without_calls = true;
        bool use_ssl = false;
        std::string ssl_cert_path;
        std::string ssl_key_path;
        std::string ssl_ca_path;
        std::chrono::milliseconds connection_timeout = std::chrono::milliseconds(5000);
        std::chrono::milliseconds request_timeout = std::chrono::milliseconds(30000);
        int max_retry_attempts = 3;
        std::chrono::milliseconds retry_delay = std::chrono::milliseconds(1000);
    };

    /**
     * @brief 推理服务接口
     */
    class IInferenceService {
    public:
        virtual ~IInferenceService() = default;
        
        virtual Task<Result<InferenceResult>> infer_async(const InferenceRequest& request) = 0;
        virtual Task<Result<BatchInferenceResult>> batch_infer_async(const BatchInferenceRequest& request) = 0;
        virtual Task<Result<void>> stream_infer_async(
            const InferenceRequest& request,
            std::function<void(const StreamInferenceResponse&)> callback
        ) = 0;
        virtual Task<Result<LoadModelResponse>> load_model_async(const LoadModelRequest& request) = 0;
        virtual Task<Result<UnloadModelResponse>> unload_model_async(const UnloadModelRequest& request) = 0;
        virtual Task<Result<ListModelsResponse>> list_models_async(const ListModelsRequest& request) = 0;
    };

    /**
     * @brief 系统服务接口
     */
    class ISystemService {
    public:
        virtual ~ISystemService() = default;
        
        virtual Task<Result<SystemInfoResponse>> get_system_info_async(const SystemInfoRequest& request) = 0;
        virtual Task<Result<MetricsResponse>> get_performance_metrics_async(const MetricsRequest& request) = 0;
        virtual Task<Result<ResourceResponse>> manage_resources_async(const ResourceRequest& request) = 0;
        virtual Task<Result<SystemInfoResponse>> health_check_async() = 0;
    };

    /**
     * @brief 插件服务接口
     */
    class IPluginService {
    public:
        virtual ~IPluginService() = default;
        
        virtual Task<Result<LoadPluginResponse>> load_plugin_async(const LoadPluginRequest& request) = 0;
        virtual Task<Result<UnloadPluginResponse>> unload_plugin_async(const UnloadPluginRequest& request) = 0;
        virtual Task<Result<ListPluginsResponse>> list_plugins_async(const ListPluginsRequest& request) = 0;
        virtual Task<Result<PluginCallResponse>> call_plugin_async(const PluginCallRequest& request) = 0;
    };

    /**
     * @brief 高性能gRPC服务器实现
     */
    class GrpcServer {
    public:
        /**
         * @brief 构造函数
         */
        explicit GrpcServer(const GrpcServerConfig& config = {});

        /**
         * @brief 析构函数
         */
        ~GrpcServer();

        /**
         * @brief 注册推理服务
         */
        void register_inference_service(std::shared_ptr<IInferenceService> service);

        /**
         * @brief 注册系统服务
         */
        void register_system_service(std::shared_ptr<ISystemService> service);

        /**
         * @brief 注册插件服务
         */
        void register_plugin_service(std::shared_ptr<IPluginService> service);

        /**
         * @brief 启动服务器（异步）
         */
        Task<Result<void>> start_async();

        /**
         * @brief 停止服务器
         */
        Task<Result<void>> stop_async(std::chrono::milliseconds timeout = std::chrono::milliseconds(5000));

        /**
         * @brief 等待服务器停止
         */
        void wait_for_shutdown();

        /**
         * @brief 检查服务器状态
         */
        bool is_running() const;

        /**
         * @brief 获取服务器地址
         */
        std::string get_server_address() const;

        /**
         * @brief 获取性能统计
         */
        struct ServerStats {
            uint64_t total_requests = 0;
            uint64_t active_requests = 0;
            uint64_t failed_requests = 0;
            double average_latency_ms = 0.0;
            std::chrono::steady_clock::time_point start_time;
        };
        ServerStats get_stats() const;

        /**
         * @brief 更新配置
         */
        void update_config(const GrpcServerConfig& config);

    private:
        class Impl;
        std::unique_ptr<Impl> pimpl_;
    };

    /**
     * @brief 高性能gRPC客户端
     */
    class GrpcClient {
    public:
        /**
         * @brief 构造函数
         */
        explicit GrpcClient(const GrpcClientConfig& config = {});

        /**
         * @brief 析构函数
         */
        ~GrpcClient();

        /**
         * @brief 连接到服务器
         */
        Task<Result<void>> connect_async();

        /**
         * @brief 断开连接
         */
        void disconnect();

        /**
         * @brief 检查连接状态
         */
        bool is_connected() const;

        // ========== 推理服务调用 ==========

        /**
         * @brief 推理调用
         */
        Task<Result<InferenceResult>> infer_async(const InferenceRequest& request);

        /**
         * @brief 批量推理调用
         */
        Task<Result<BatchInferenceResult>> batch_infer_async(const BatchInferenceRequest& request);

        /**
         * @brief 流式推理调用
         */
        Task<Result<void>> stream_infer_async(
            const InferenceRequest& request,
            std::function<void(const StreamInferenceResponse&)> callback
        );

        /**
         * @brief 加载模型
         */
        Task<Result<LoadModelResponse>> load_model_async(const LoadModelRequest& request);

        /**
         * @brief 卸载模型
         */
        Task<Result<UnloadModelResponse>> unload_model_async(const UnloadModelRequest& request);

        /**
         * @brief 获取模型列表
         */
        Task<Result<ListModelsResponse>> list_models_async(const ListModelsRequest& request);

        // ========== 系统服务调用 ==========

        /**
         * @brief 获取系统信息
         */
        Task<Result<SystemInfoResponse>> get_system_info_async(const SystemInfoRequest& request);

        /**
         * @brief 获取性能指标
         */
        Task<Result<MetricsResponse>> get_performance_metrics_async(const MetricsRequest& request);

        /**
         * @brief 资源管理
         */
        Task<Result<ResourceResponse>> manage_resources_async(const ResourceRequest& request);

        /**
         * @brief 健康检查
         */
        Task<Result<SystemInfoResponse>> health_check_async();

        // ========== 插件服务调用 ==========

        /**
         * @brief 加载插件
         */
        Task<Result<LoadPluginResponse>> load_plugin_async(const LoadPluginRequest& request);

        /**
         * @brief 卸载插件
         */
        Task<Result<UnloadPluginResponse>> unload_plugin_async(const UnloadPluginRequest& request);

        /**
         * @brief 获取插件列表
         */
        Task<Result<ListPluginsResponse>> list_plugins_async(const ListPluginsRequest& request);

        /**
         * @brief 调用插件
         */
        Task<Result<PluginCallResponse>> call_plugin_async(const PluginCallRequest& request);

        /**
         * @brief 获取客户端统计
         */
        struct ClientStats {
            uint64_t total_requests = 0;
            uint64_t successful_requests = 0;
            uint64_t failed_requests = 0;
            double average_latency_ms = 0.0;
            std::chrono::steady_clock::time_point start_time;
        };
        ClientStats get_stats() const;

    private:
        class Impl;
        std::unique_ptr<Impl> pimpl_;
    };

    /**
     * @brief gRPC连接池管理器
     */
    class ConnectionPool {
    public:
        /**
         * @brief 构造函数
         */
        explicit ConnectionPool(const GrpcClientConfig& config, size_t pool_size = 10);

        /**
         * @brief 析构函数
         */
        ~ConnectionPool();

        /**
         * @brief 获取连接
         */
        std::shared_ptr<GrpcClient> acquire_connection();

        /**
         * @brief 释放连接
         */
        void release_connection(std::shared_ptr<GrpcClient> client);

        /**
         * @brief 获取池统计信息
         */
        struct PoolStats {
            size_t pool_size = 0;
            size_t active_connections = 0;
            size_t available_connections = 0;
            uint64_t total_acquisitions = 0;
        };
        PoolStats get_pool_stats() const;

    private:
        class Impl;
        std::unique_ptr<Impl> pimpl_;
    };

    /**
     * @brief gRPC工具函数
     */
    namespace utils {
        
        /**
         * @brief 创建默认服务器配置
         */
        GrpcServerConfig create_default_server_config();

        /**
         * @brief 创建默认客户端配置
         */
        GrpcClientConfig create_default_client_config();

        /**
         * @brief 创建SSL服务器凭据
         */
        std::shared_ptr<::grpc::ServerCredentials> create_ssl_server_credentials(
            const std::string& cert_path,
            const std::string& key_path,
            const std::string& ca_path = ""
        );

        /**
         * @brief 创建SSL通道凭据
         */
        std::shared_ptr<::grpc::ChannelCredentials> create_ssl_channel_credentials(
            const std::string& cert_path = "",
            const std::string& key_path = "",
            const std::string& ca_path = ""
        );

        /**
         * @brief 配置通道参数
         */
        ::grpc::ChannelArguments configure_channel_args(const GrpcClientConfig& config);

        /**
         * @brief 错误代码转换
         */
        ErrorCode grpc_status_to_error_code(::grpc::StatusCode status);

        /**
         * @brief 创建错误信息
         */
        ErrorInfo create_error_info(::grpc::StatusCode status, const std::string& message);

        /**
         * @brief 检查gRPC可用性
         */
        bool is_grpc_available();

        /**
         * @brief 获取gRPC版本
         */
        std::string get_grpc_version();
    }

} // namespace hushell::core::grpc

#endif // HUSHELL_ENABLE_GRPC