#include "../include/model_engine.hpp"
#include "../include/sys_manager.hpp"
#include "../include/grpc_server.hpp"
#include "../include/plugin_loader.hpp"
#include "../include/common.hpp"
#include <iostream>
#include <memory>
#include <signal.h>

using namespace ai_assistant;

// 全局变量用于信号处理
std::unique_ptr<GrpcServer> g_server;
bool g_running = true;

void signal_handler(int signal) {
    Logger::info("Received signal " + std::to_string(signal) + ", shutting down...");
    g_running = false;
    
    if (g_server) {
        g_server->stop();
    }
}

void print_usage(const char* program_name) {
    std::cout << "Usage: " << program_name << " [options]\n"
              << "Options:\n"
              << "  --port PORT          gRPC server port (default: 50051)\n"
              << "  --config PATH        Configuration file path\n"
              << "  --model PATH         Local model file path\n"
              << "  --plugins DIR        Plugin directory path\n"
              << "  --log-level LEVEL    Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)\n"
              << "  --help               Show this help message\n";
}

LogLevel parse_log_level(const std::string& level) {
    if (level == "DEBUG") return LogLevel::DEBUG;
    if (level == "INFO") return LogLevel::INFO;
    if (level == "WARNING") return LogLevel::WARNING;
    if (level == "ERROR") return LogLevel::ERROR;
    if (level == "CRITICAL") return LogLevel::CRITICAL;
    return LogLevel::INFO;
}

int main(int argc, char* argv[]) {
    // 默认参数
    int port = 50051;
    std::string config_path = "config/app.yaml";
    std::string model_path;
    std::string plugins_dir = "plugins/";
    LogLevel log_level = LogLevel::INFO;
    
    // 解析命令行参数
    for (int i = 1; i < argc; i++) {
        std::string arg = argv[i];
        
        if (arg == "--help") {
            print_usage(argv[0]);
            return 0;
        } else if (arg == "--port" && i + 1 < argc) {
            port = std::atoi(argv[++i]);
        } else if (arg == "--config" && i + 1 < argc) {
            config_path = argv[++i];
        } else if (arg == "--model" && i + 1 < argc) {
            model_path = argv[++i];
        } else if (arg == "--plugins" && i + 1 < argc) {
            plugins_dir = argv[++i];
        } else if (arg == "--log-level" && i + 1 < argc) {
            log_level = parse_log_level(argv[++i]);
        } else {
            std::cerr << "Unknown argument: " << arg << std::endl;
            print_usage(argv[0]);
            return 1;
        }
    }
    
    // 设置日志级别
    Logger::set_level(log_level);
    
    Logger::info("=== AI Assistant Core Server Starting ===");
    Logger::info("Port: " + std::to_string(port));
    Logger::info("Config: " + config_path);
    Logger::info("Log Level: " + std::to_string(static_cast<int>(log_level)));
    
    // 注册信号处理器
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);
    
    try {
        // 初始化系统管理器
        Logger::info("Initializing System Manager...");
        auto sys_manager = std::make_unique<SystemManager>();
        
        // 获取系统信息
        auto sys_info = sys_manager->get_system_info();
        Logger::info("System Info - CPU Cores: " + std::to_string(sys_info.cpu_cores) + 
                    ", Memory: " + std::to_string(sys_info.memory_total_gb) + "GB" +
                    ", OS: " + sys_info.os_info);
        
        // 检查CUDA支持
        if (sys_manager->is_cuda_available()) {
            Logger::info("CUDA is available");
            auto gpu_info = sys_manager->get_gpu_info();
            for (const auto& gpu : gpu_info) {
                Logger::info("GPU: " + gpu);
            }
        } else {
            Logger::info("CUDA is not available, using CPU inference");
        }
        
        // 启动系统监控
        sys_manager->start_monitoring(5000); // 5秒间隔
        
        // 初始化模型引擎
        Logger::info("Initializing Model Engine...");
        auto model_engine = std::make_unique<ModelEngine>();
        
        if (!model_engine->initialize(config_path)) {
            Logger::error("Failed to initialize Model Engine");
            return 1;
        }
        
        // 加载本地模型（如果指定）
        if (!model_path.empty()) {
            Logger::info("Loading local model: " + model_path);
            if (!model_engine->load_local_model(model_path)) {
                Logger::warning("Failed to load local model, will use cloud API");
            }
        }
        
        // 初始化插件加载器
        Logger::info("Initializing Plugin Loader...");
        auto plugin_loader = std::make_unique<PluginLoader>();
        
        // 自动发现并加载插件
        auto discovered_plugins = plugin_loader->discover_plugins(plugins_dir);
        Logger::info("Discovered " + std::to_string(discovered_plugins.size()) + " plugins");
        
        for (const auto& plugin_path : discovered_plugins) {
            if (plugin_loader->validate_plugin(plugin_path)) {
                if (plugin_loader->load_plugin(plugin_path)) {
                    Logger::info("Loaded plugin: " + plugin_path);
                } else {
                    Logger::warning("Failed to load plugin: " + plugin_path);
                }
            } else {
                Logger::debug("Invalid plugin: " + plugin_path);
            }
        }
        
        // 启动gRPC服务器
        Logger::info("Starting gRPC Server...");
        g_server = std::make_unique<GrpcServer>();
        
        if (!g_server->start(port)) {
            Logger::error("Failed to start gRPC server");
            return 1;
        }
        
        // 健康检查
        Logger::info("Performing health checks...");
        bool health_ok = true;
        
        if (!model_engine->is_healthy()) {
            Logger::warning("Model Engine health check failed");
            health_ok = false;
        }
        
        if (!g_server->is_running()) {
            Logger::error("gRPC Server health check failed");
            health_ok = false;
        }
        
        if (health_ok) {
            Logger::info("=== AI Assistant Core Server Started Successfully ===");
            Logger::info("Server is ready to accept connections on port " + std::to_string(port));
        } else {
            Logger::warning("Server started with some components in unhealthy state");
        }
        
        // 主循环
        while (g_running) {
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
            
            // 定期健康检查
            static auto last_health_check = std::chrono::steady_clock::now();
            auto now = std::chrono::steady_clock::now();
            
            if (std::chrono::duration_cast<std::chrono::seconds>(now - last_health_check).count() >= 30) {
                // 每30秒进行一次健康检查
                if (!model_engine->is_healthy()) {
                    Logger::warning("Model Engine became unhealthy");
                }
                
                last_health_check = now;
            }
        }
        
        // 清理资源
        Logger::info("Shutting down components...");
        
        sys_manager->stop_monitoring();
        plugin_loader->unload_all_plugins();
        
        Logger::info("=== AI Assistant Core Server Shutdown Complete ===");
        return 0;
        
    } catch (const std::exception& e) {
        Logger::critical("Fatal error: " + std::string(e.what()));
        return 1;
    } catch (...) {
        Logger::critical("Unknown fatal error occurred");
        return 1;
    }
}