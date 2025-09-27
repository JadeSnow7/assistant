#pragma once

#include <string>
#include <vector>
#include <map>
#include <memory>
#include <functional>

namespace ai_assistant {

// 插件信息结构
struct PluginInfo {
    std::string name;
    std::string version;
    std::string description;
    std::string author;
    std::vector<std::string> capabilities;
    std::string config_schema;
    bool enabled = false;
};

// 插件接口基类
class IPlugin {
public:
    virtual ~IPlugin() = default;
    
    // 插件初始化
    virtual bool initialize(const std::string& config) = 0;
    
    // 执行插件功能
    virtual std::string execute(const std::string& command, 
                               const std::map<std::string, std::string>& params) = 0;
    
    // 获取插件信息
    virtual PluginInfo get_info() const = 0;
    
    // 清理资源
    virtual void cleanup() = 0;
    
    // 健康检查
    virtual bool is_healthy() const = 0;
};

// 插件工厂函数类型
using CreatePluginFunc = std::function<std::unique_ptr<IPlugin>()>;
using DestroyPluginFunc = std::function<void(IPlugin*)>;

/**
 * 插件加载管理器
 * 支持动态加载C++和Python插件
 */
class PluginLoader {
public:
    PluginLoader();
    ~PluginLoader();

    // 扫描插件目录
    void scan_plugins(const std::string& plugin_dir);
    
    // 加载C++插件
    bool load_cpp_plugin(const std::string& plugin_path);
    
    // 加载Python插件
    bool load_python_plugin(const std::string& plugin_path);
    
    // 卸载插件
    bool unload_plugin(const std::string& plugin_name);
    
    // 获取所有插件信息
    std::vector<PluginInfo> get_all_plugins() const;
    
    // 获取已启用的插件
    std::vector<std::string> get_enabled_plugins() const;
    
    // 启用/禁用插件
    bool enable_plugin(const std::string& plugin_name);
    bool disable_plugin(const std::string& plugin_name);
    
    // 执行插件命令
    std::string execute_plugin(const std::string& plugin_name,
                              const std::string& command,
                              const std::map<std::string, std::string>& params);
    
    // 检查插件是否存在
    bool has_plugin(const std::string& plugin_name) const;
    
    // 获取插件能力列表
    std::vector<std::string> get_plugin_capabilities(const std::string& plugin_name) const;
    
    // 重新加载插件
    bool reload_plugin(const std::string& plugin_name);

private:
    class Impl;
    std::unique_ptr<Impl> pimpl_;
};

} // namespace ai_assistant

// C插件导出宏
#define EXPORT_PLUGIN(ClassName) \
    extern "C" { \
        ai_assistant::IPlugin* create_plugin() { \
            return new ClassName(); \
        } \
        void destroy_plugin(ai_assistant::IPlugin* plugin) { \
            delete plugin; \
        } \
    }