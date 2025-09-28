#pragma once

#include "common.hpp"
#include <grpcpp/grpcpp.h>
#include <thread>
#include <atomic>
#include <memory>

namespace ai_assistant {

/**
 * gRPC服务器
 * 为Python应用层提供高性能的C++服务接口
 */
class GRPCServer {
public:
    GRPCServer();
    ~GRPCServer();

    // 启动服务器
    bool start(const std::string& address = "0.0.0.0:50051");
    
    // 停止服务器
    void stop();
    
    // 检查服务器是否运行
    bool is_running() const;
    
    // 等待服务器关闭
    void wait_for_shutdown();
    
    // 健康检查
    bool health_check() const;

private:
    class Impl;
    std::unique_ptr<Impl> pimpl_;
    
    std::unique_ptr<grpc::Server> server_;
    std::atomic<bool> running_;
    std::thread server_thread_;
    
    void run_server(const std::string& address);
};

} // namespace ai_assistant