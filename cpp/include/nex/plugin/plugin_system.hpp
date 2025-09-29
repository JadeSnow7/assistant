#pragma once

#include "../core/async_types.hpp"
#include "../platform_config.h"
#include <string>
#include <vector>
#include <unordered_map>
#include <memory>
#include <functional>
#include <filesystem>
#include <chrono>
#include <any>

namespace hushell::plugin {

    /**
     * @brief 插件版本信息
     */
    struct PluginVersion {
        int major = 1;
        int minor = 0;
        int patch = 0;
        std::string suffix;

        std::string to_string() const {
            std::string version = std::to_string(major) + "." + 
                                 std::to_string(minor) + "." + 
                                 std::to_string(patch);
            if (!suffix.empty()) {
                version += "-" + suffix;
            }
            return version;
        }

        bool is_compatible(const PluginVersion& other) const {
            return major == other.major && minor >= other.minor;
        }
    };

    /**
     * @brief 插件元数据
     */
    struct PluginMetadata {
        std::string name;
        std::string display_name;
        std::string description;
        PluginVersion version;
        std::string author;
        std::string license;
        std::string website;
        
        // 依赖信息
        std::vector<std::string> dependencies;
        PluginVersion min_core_version;
        std::vector<std::string> supported_platforms;
        
        // 配置信息
        std::unordered_map<std::string, std::string> default_config;
        std::unordered_map<std::string, std::string> capabilities;
        
        // 文件信息
        std::filesystem::path plugin_path;
        std::string entry_point;
        size_t file_size = 0;
        std::chrono::system_clock::time_point last_modified;
    };

    /**
     * @brief 插件状态
     */
    enum class PluginStatus {
        UNKNOWN = 0,
        LOADED = 1,
        INITIALIZED = 2,
        RUNNING = 3,
        PAUSED = 4,
        ERROR = 5,
        UNLOADING = 6
    };

    /**
     * @brief 插件错误信息
     */
    struct PluginError {
        int code = 0;
        std::string message;
        std::string details;
        std::chrono::steady_clock::time_point timestamp;
    };

    /**
     * @brief 插件上下文
     */
    class PluginContext {
    public:
        virtual ~PluginContext() = default;

        /**
         * @brief 获取核心API接口
         */
        virtual void* get_core_api(const std::string& api_name) = 0;

        /**
         * @brief 记录日志
         */
        virtual void log(const std::string& level, const std::string& message) = 0;

        /**
         * @brief 获取配置值
         */
        virtual std::string get_config(const std::string& key, const std::string& default_value = "") = 0;

        /**
         * @brief 设置配置值
         */
        virtual void set_config(const std::string& key, const std::string& value) = 0;

        /**
         * @brief 调用其他插件
         */
        virtual std::any call_plugin(const std::string& plugin_name, const std::string& method, 
                                   const std::vector<std::any>& args) = 0;

        /**
         * @brief 注册事件监听器
         */
        virtual void register_event_listener(const std::string& event_name, 
                                           std::function<void(const std::any&)> callback) = 0;

        /**
         * @brief 触发事件
         */
        virtual void emit_event(const std::string& event_name, const std::any& data) = 0;

        /**
         * @brief 获取插件数据目录
         */
        virtual std::filesystem::path get_plugin_data_dir() const = 0;

        /**
         * @brief 获取临时目录
         */
        virtual std::filesystem::path get_temp_dir() const = 0;

        /**
         * @brief 分配内存
         */
        virtual void* allocate_memory(size_t size) = 0;

        /**
         * @brief 释放内存
         */
        virtual void deallocate_memory(void* ptr) = 0;
    };

    /**
     * @brief 插件接口基类
     */
    class IPlugin {
    public:
        virtual ~IPlugin() = default;

        // ========== 生命周期方法 ==========

        /**
         * @brief 获取插件元数据
         */
        virtual PluginMetadata get_metadata() const = 0;

        /**
         * @brief 初始化插件
         */
        virtual core::Result<void> initialize(PluginContext* context) = 0;

        /**
         * @brief 启动插件
         */
        virtual core::Result<void> start() = 0;

        /**
         * @brief 停止插件
         */
        virtual core::Result<void> stop() = 0;

        /**
         * @brief 清理插件
         */
        virtual core::Result<void> cleanup() = 0;

        // ========== 状态查询 ==========

        /**
         * @brief 获取插件状态
         */
        virtual PluginStatus get_status() const = 0;

        /**
         * @brief 检查插件健康状态
         */
        virtual bool is_healthy() const = 0;

        /**
         * @brief 获取最后的错误信息
         */
        virtual std::optional<PluginError> get_last_error() const = 0;

        // ========== 功能接口 ==========

        /**
         * @brief 调用插件方法
         */
        virtual core::Result<std::any> call_method(const std::string& method_name, 
                                                  const std::vector<std::any>& args) = 0;

        /**
         * @brief 获取插件支持的方法列表
         */
        virtual std::vector<std::string> get_supported_methods() const = 0;

        /**
         * @brief 获取方法签名
         */
        virtual std::string get_method_signature(const std::string& method_name) const = 0;

        // ========== 配置管理 ==========

        /**
         * @brief 更新配置
         */
        virtual core::Result<void> update_config(const std::unordered_map<std::string, std::string>& config) = 0;

        /**
         * @brief 获取当前配置
         */
        virtual std::unordered_map<std::string, std::string> get_current_config() const = 0;

        /**
         * @brief 验证配置
         */
        virtual core::Result<void> validate_config(const std::unordered_map<std::string, std::string>& config) const = 0;
    };

    /**
     * @brief 插件基类实现
     */
    class PluginBase : public IPlugin {
    public:
        explicit PluginBase(const PluginMetadata& metadata);
        virtual ~PluginBase() = default;

        // 实现IPlugin接口
        PluginMetadata get_metadata() const override;
        PluginStatus get_status() const override;
        bool is_healthy() const override;
        std::optional<PluginError> get_last_error() const override;
        std::vector<std::string> get_supported_methods() const override;
        std::string get_method_signature(const std::string& method_name) const override;
        std::unordered_map<std::string, std::string> get_current_config() const override;

    protected:
        /**
         * @brief 设置插件状态
         */
        void set_status(PluginStatus status);

        /**
         * @brief 设置错误信息
         */
        void set_error(int code, const std::string& message, const std::string& details = "");

        /**
         * @brief 注册方法
         */
        void register_method(const std::string& method_name, const std::string& signature,
                           std::function<core::Result<std::any>(const std::vector<std::any>&)> handler);

        /**
         * @brief 获取插件上下文
         */
        PluginContext* get_context() const;

        /**
         * @brief 记录日志
         */
        void log_info(const std::string& message);
        void log_warning(const std::string& message);
        void log_error(const std::string& message);

    private:
        PluginMetadata metadata_;
        std::atomic<PluginStatus> status_{PluginStatus::UNKNOWN};
        std::optional<PluginError> last_error_;
        PluginContext* context_ = nullptr;
        std::unordered_map<std::string, std::string> current_config_;
        
        // 方法注册表
        struct MethodInfo {
            std::string signature;
            std::function<core::Result<std::any>(const std::vector<std::any>&)> handler;
        };
        std::unordered_map<std::string, MethodInfo> registered_methods_;
        mutable std::mutex methods_mutex_;
        mutable std::mutex config_mutex_;

        friend class PluginManager;
    };

    /**
     * @brief 插件加载器接口
     */
    class IPluginLoader {
    public:
        virtual ~IPluginLoader() = default;

        /**
         * @brief 检查是否支持加载指定文件
         */
        virtual bool can_load(const std::filesystem::path& plugin_path) = 0;

        /**
         * @brief 加载插件
         */
        virtual core::Result<std::unique_ptr<IPlugin>> load_plugin(const std::filesystem::path& plugin_path) = 0;

        /**
         * @brief 卸载插件
         */
        virtual core::Result<void> unload_plugin(std::unique_ptr<IPlugin> plugin) = 0;

        /**
         * @brief 获取加载器名称
         */
        virtual std::string get_loader_name() const = 0;

        /**
         * @brief 获取支持的文件扩展名
         */
        virtual std::vector<std::string> get_supported_extensions() const = 0;
    };

    /**
     * @brief C++动态库插件加载器
     */
    class NativePluginLoader : public IPluginLoader {
    public:
        NativePluginLoader();
        ~NativePluginLoader();

        bool can_load(const std::filesystem::path& plugin_path) override;
        core::Result<std::unique_ptr<IPlugin>> load_plugin(const std::filesystem::path& plugin_path) override;
        core::Result<void> unload_plugin(std::unique_ptr<IPlugin> plugin) override;
        std::string get_loader_name() const override;
        std::vector<std::string> get_supported_extensions() const override;

    private:
        struct LoadedLibrary {
            void* handle = nullptr;
            std::filesystem::path path;
            std::chrono::steady_clock::time_point load_time;
        };
        std::unordered_map<std::string, LoadedLibrary> loaded_libraries_;
        std::mutex libraries_mutex_;
    };

    /**
     * @brief 插件管理器
     */
    class PluginManager {
    public:
        /**
         * @brief 获取单例实例
         */
        static PluginManager& instance();

        /**
         * @brief 初始化插件管理器
         */
        core::Result<void> initialize(const std::unordered_map<std::string, std::string>& config = {});

        /**
         * @brief 关闭插件管理器
         */
        void shutdown();

        // ========== 插件加载器管理 ==========

        /**
         * @brief 注册插件加载器
         */
        void register_loader(std::unique_ptr<IPluginLoader> loader);

        /**
         * @brief 获取加载器列表
         */
        std::vector<std::string> get_loader_names() const;

        // ========== 插件生命周期管理 ==========

        /**
         * @brief 加载插件
         */
        core::Task<core::Result<std::string>> load_plugin_async(const std::filesystem::path& plugin_path);

        /**
         * @brief 卸载插件
         */
        core::Task<core::Result<void>> unload_plugin_async(const std::string& plugin_name);

        /**
         * @brief 重新加载插件
         */
        core::Task<core::Result<void>> reload_plugin_async(const std::string& plugin_name);

        /**
         * @brief 启动插件
         */
        core::Task<core::Result<void>> start_plugin_async(const std::string& plugin_name);

        /**
         * @brief 停止插件
         */
        core::Task<core::Result<void>> stop_plugin_async(const std::string& plugin_name);

        // ========== 插件查询 ==========

        /**
         * @brief 获取已加载的插件列表
         */
        std::vector<std::string> get_loaded_plugins() const;

        /**
         * @brief 获取插件元数据
         */
        std::optional<PluginMetadata> get_plugin_metadata(const std::string& plugin_name) const;

        /**
         * @brief 获取插件状态
         */
        std::optional<PluginStatus> get_plugin_status(const std::string& plugin_name) const;

        /**
         * @brief 检查插件是否存在
         */
        bool has_plugin(const std::string& plugin_name) const;

        /**
         * @brief 检查插件是否正在运行
         */
        bool is_plugin_running(const std::string& plugin_name) const;

        // ========== 插件调用 ==========

        /**
         * @brief 调用插件方法
         */
        core::Task<core::Result<std::any>> call_plugin_async(const std::string& plugin_name, 
                                                            const std::string& method_name,
                                                            const std::vector<std::any>& args);

        /**
         * @brief 广播事件到所有插件
         */
        void broadcast_event(const std::string& event_name, const std::any& data);

        // ========== 插件发现 ==========

        /**
         * @brief 扫描目录查找插件
         */
        std::vector<std::filesystem::path> scan_plugins(const std::filesystem::path& directory, 
                                                       bool recursive = true);

        /**
         * @brief 自动加载目录中的插件
         */
        core::Task<std::vector<core::Result<std::string>>> auto_load_plugins_async(
            const std::filesystem::path& directory);

        // ========== 配置管理 ==========

        /**
         * @brief 更新插件配置
         */
        core::Result<void> update_plugin_config(const std::string& plugin_name,
                                               const std::unordered_map<std::string, std::string>& config);

        /**
         * @brief 获取插件配置
         */
        std::unordered_map<std::string, std::string> get_plugin_config(const std::string& plugin_name) const;

        // ========== 统计信息 ==========

        /**
         * @brief 获取插件管理器统计信息
         */
        struct ManagerStats {
            size_t total_plugins = 0;
            size_t running_plugins = 0;
            size_t failed_plugins = 0;
            size_t registered_loaders = 0;
            std::chrono::steady_clock::time_point start_time;
            std::unordered_map<std::string, size_t> plugins_by_status;
        };
        ManagerStats get_stats() const;

    private:
        PluginManager() = default;
        ~PluginManager() = default;

        // 禁用拷贝和移动
        PluginManager(const PluginManager&) = delete;
        PluginManager& operator=(const PluginManager&) = delete;

        class PluginContextImpl;
        
        struct PluginInfo {
            std::unique_ptr<IPlugin> instance;
            std::unique_ptr<PluginContextImpl> context;
            std::filesystem::path source_path;
            std::chrono::steady_clock::time_point load_time;
        };

        mutable std::shared_mutex plugins_mutex_;
        std::unordered_map<std::string, PluginInfo> loaded_plugins_;
        
        mutable std::shared_mutex loaders_mutex_;
        std::vector<std::unique_ptr<IPluginLoader>> plugin_loaders_;

        std::atomic<bool> initialized_{false};
        std::chrono::steady_clock::time_point start_time_;
    };

    /**
     * @brief 插件注册宏
     */
    #define HUSHELL_PLUGIN_EXPORT extern "C" HUSHELL_API

    /**
     * @brief 插件工厂函数类型
     */
    using PluginCreateFunc = IPlugin* (*)();
    using PluginDestroyFunc = void (*)(IPlugin*);

    /**
     * @brief 标准插件注册宏
     */
    #define REGISTER_HUSHELL_PLUGIN(PluginClass) \
        HUSHELL_PLUGIN_EXPORT IPlugin* create_plugin() { \
            return new PluginClass(); \
        } \
        HUSHELL_PLUGIN_EXPORT void destroy_plugin(IPlugin* plugin) { \
            delete plugin; \
        } \
        HUSHELL_PLUGIN_EXPORT const char* get_plugin_api_version() { \
            return "1.0.0"; \
        }

} // namespace hushell::plugin