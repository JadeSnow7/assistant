#pragma once

#include "plugin_system.hpp"
#include <json/json.h>  // 假设使用nlohmann/json

namespace hushell::plugin {

    /**
     * @brief 简化的插件基类，提供常用功能的默认实现
     */
    template<typename ConfigType = std::unordered_map<std::string, std::string>>
    class SimplePluginBase : public PluginBase {
    public:
        explicit SimplePluginBase(const PluginMetadata& metadata) : PluginBase(metadata) {}

        // ========== 简化的生命周期管理 ==========

        /**
         * @brief 默认初始化实现
         */
        core::Result<void> initialize(PluginContext* context) override {
            set_status(PluginStatus::LOADED);
            
            try {
                auto result = on_initialize(context);
                if (result.is_success()) {
                    set_status(PluginStatus::INITIALIZED);
                }
                return result;
            } catch (const std::exception& e) {
                set_error(1, "Initialize failed", e.what());
                return core::Result<void>::error(core::ErrorCode::INTERNAL_ERROR, e.what());
            }
        }

        /**
         * @brief 默认启动实现
         */
        core::Result<void> start() override {
            if (get_status() != PluginStatus::INITIALIZED) {
                return core::Result<void>::error(core::ErrorCode::INVALID_ARGUMENT, "Plugin not initialized");
            }

            try {
                auto result = on_start();
                if (result.is_success()) {
                    set_status(PluginStatus::RUNNING);
                }
                return result;
            } catch (const std::exception& e) {
                set_error(2, "Start failed", e.what());
                return core::Result<void>::error(core::ErrorCode::INTERNAL_ERROR, e.what());
            }
        }

        /**
         * @brief 默认停止实现
         */
        core::Result<void> stop() override {
            if (get_status() != PluginStatus::RUNNING) {
                return core::Result<void>::success();
            }

            try {
                auto result = on_stop();
                if (result.is_success()) {
                    set_status(PluginStatus::INITIALIZED);
                }
                return result;
            } catch (const std::exception& e) {
                set_error(3, "Stop failed", e.what());
                return core::Result<void>::error(core::ErrorCode::INTERNAL_ERROR, e.what());
            }
        }

        /**
         * @brief 默认清理实现
         */
        core::Result<void> cleanup() override {
            try {
                auto result = on_cleanup();
                set_status(PluginStatus::UNKNOWN);
                return result;
            } catch (const std::exception& e) {
                set_error(4, "Cleanup failed", e.what());
                return core::Result<void>::error(core::ErrorCode::INTERNAL_ERROR, e.what());
            }
        }

        // ========== 方法调用 ==========

        /**
         * @brief 默认方法调用实现
         */
        core::Result<std::any> call_method(const std::string& method_name, 
                                          const std::vector<std::any>& args) override {
            try {
                return on_method_call(method_name, args);
            } catch (const std::exception& e) {
                set_error(5, "Method call failed: " + method_name, e.what());
                return core::Result<std::any>::error(core::ErrorCode::INTERNAL_ERROR, e.what());
            }
        }

        // ========== 配置管理 ==========

        /**
         * @brief 更新配置
         */
        core::Result<void> update_config(const std::unordered_map<std::string, std::string>& config) override {
            try {
                ConfigType typed_config;
                if constexpr (std::is_same_v<ConfigType, std::unordered_map<std::string, std::string>>) {
                    typed_config = config;
                } else {
                    // 转换为自定义配置类型
                    typed_config = convert_config(config);
                }

                auto result = validate_config(config);
                if (result.is_error()) {
                    return result;
                }

                config_ = typed_config;
                return on_config_updated(typed_config);
            } catch (const std::exception& e) {
                set_error(6, "Config update failed", e.what());
                return core::Result<void>::error(core::ErrorCode::INTERNAL_ERROR, e.what());
            }
        }

        /**
         * @brief 验证配置
         */
        core::Result<void> validate_config(const std::unordered_map<std::string, std::string>& config) const override {
            return on_validate_config(config);
        }

    protected:
        // ========== 子类需要实现的虚函数 ==========

        /**
         * @brief 初始化回调
         */
        virtual core::Result<void> on_initialize(PluginContext* context) = 0;

        /**
         * @brief 启动回调
         */
        virtual core::Result<void> on_start() = 0;

        /**
         * @brief 停止回调
         */
        virtual core::Result<void> on_stop() = 0;

        /**
         * @brief 清理回调
         */
        virtual core::Result<void> on_cleanup() = 0;

        /**
         * @brief 方法调用回调
         */
        virtual core::Result<std::any> on_method_call(const std::string& method_name, 
                                                     const std::vector<std::any>& args) = 0;

        /**
         * @brief 配置更新回调
         */
        virtual core::Result<void> on_config_updated(const ConfigType& config) = 0;

        /**
         * @brief 配置验证回调
         */
        virtual core::Result<void> on_validate_config(const std::unordered_map<std::string, std::string>& config) const = 0;

        // ========== 工具方法 ==========

        /**
         * @brief 获取当前配置
         */
        const ConfigType& get_config() const { return config_; }

        /**
         * @brief 注册简单方法
         */
        template<typename ReturnType, typename... Args>
        void register_simple_method(const std::string& method_name,
                                   std::function<ReturnType(Args...)> handler) {
            auto wrapper = [handler](const std::vector<std::any>& args) -> core::Result<std::any> {
                try {
                    if (args.size() != sizeof...(Args)) {
                        return core::Result<std::any>::error(core::ErrorCode::INVALID_ARGUMENT, 
                                                           "Argument count mismatch");
                    }

                    if constexpr (std::is_void_v<ReturnType>) {
                        call_with_args(handler, args, std::index_sequence_for<Args...>{});
                        return core::Result<std::any>::success(std::any{});
                    } else {
                        auto result = call_with_args(handler, args, std::index_sequence_for<Args...>{});
                        return core::Result<std::any>::success(std::any{result});
                    }
                } catch (const std::exception& e) {
                    return core::Result<std::any>::error(core::ErrorCode::INTERNAL_ERROR, e.what());
                }
            };

            std::string signature = generate_signature<ReturnType, Args...>();
            register_method(method_name, signature, wrapper);
        }

        /**
         * @brief 类型安全的配置获取
         */
        template<typename T>
        T get_config_value(const std::string& key, const T& default_value = T{}) const {
            if constexpr (std::is_same_v<ConfigType, std::unordered_map<std::string, std::string>>) {
                auto it = config_.find(key);
                if (it != config_.end()) {
                    return convert_string_to_type<T>(it->second);
                }
            }
            return default_value;
        }

    private:
        ConfigType config_;

        // ========== 类型转换辅助函数 ==========

        template<typename T>
        T convert_string_to_type(const std::string& str) const {
            if constexpr (std::is_same_v<T, std::string>) {
                return str;
            } else if constexpr (std::is_same_v<T, int>) {
                return std::stoi(str);
            } else if constexpr (std::is_same_v<T, double>) {
                return std::stod(str);
            } else if constexpr (std::is_same_v<T, bool>) {
                return str == "true" || str == "1";
            } else {
                static_assert(always_false_v<T>, "Unsupported config value type");
            }
        }

        template<typename T>
        static constexpr bool always_false_v = false;

        ConfigType convert_config(const std::unordered_map<std::string, std::string>& config) {
            // 默认实现：直接返回
            if constexpr (std::is_same_v<ConfigType, std::unordered_map<std::string, std::string>>) {
                return config;
            } else {
                // 子类可以重写此方法来实现自定义转换
                return ConfigType{};
            }
        }

        // ========== 方法调用辅助函数 ==========

        template<typename Func, size_t... I>
        auto call_with_args(Func&& func, const std::vector<std::any>& args, std::index_sequence<I...>) {
            return func(std::any_cast<std::tuple_element_t<I, typename function_traits<Func>::args_type>>(args[I])...);
        }

        template<typename Func>
        struct function_traits;

        template<typename R, typename... Args>
        struct function_traits<std::function<R(Args...)>> {
            using return_type = R;
            using args_type = std::tuple<Args...>;
        };

        template<typename ReturnType, typename... Args>
        std::string generate_signature() const {
            std::string signature = typeid(ReturnType).name();
            signature += "(";
            if constexpr (sizeof...(Args) > 0) {
                ((signature += typeid(Args).name() + ","), ...);
                signature.pop_back(); // 移除最后的逗号
            }
            signature += ")";
            return signature;
        }
    };

    /**
     * @brief 异步插件基类
     */
    class AsyncPluginBase : public PluginBase {
    public:
        explicit AsyncPluginBase(const PluginMetadata& metadata) : PluginBase(metadata) {}

        // ========== 异步生命周期管理 ==========

        /**
         * @brief 异步初始化
         */
        core::Result<void> initialize(PluginContext* context) override {
            set_status(PluginStatus::LOADED);
            
            // 启动异步初始化
            async_initialize_task_ = on_initialize_async(context);
            return core::Result<void>::success();
        }

        /**
         * @brief 异步启动
         */
        core::Result<void> start() override {
            if (get_status() != PluginStatus::INITIALIZED) {
                return core::Result<void>::error(core::ErrorCode::INVALID_ARGUMENT, "Plugin not initialized");
            }

            async_start_task_ = on_start_async();
            return core::Result<void>::success();
        }

        /**
         * @brief 异步停止
         */
        core::Result<void> stop() override {
            if (get_status() != PluginStatus::RUNNING) {
                return core::Result<void>::success();
            }

            async_stop_task_ = on_stop_async();
            return core::Result<void>::success();
        }

        /**
         * @brief 异步方法调用
         */
        core::Result<std::any> call_method(const std::string& method_name, 
                                          const std::vector<std::any>& args) override {
            // 这里可以实现异步方法调用的同步包装
            return on_method_call_sync(method_name, args);
        }

        /**
         * @brief 异步方法调用接口
         */
        virtual core::Task<core::Result<std::any>> call_method_async(const std::string& method_name,
                                                                    const std::vector<std::any>& args) = 0;

    protected:
        // ========== 异步回调函数 ==========

        virtual core::Task<core::Result<void>> on_initialize_async(PluginContext* context) = 0;
        virtual core::Task<core::Result<void>> on_start_async() = 0;
        virtual core::Task<core::Result<void>> on_stop_async() = 0;
        virtual core::Task<core::Result<void>> on_cleanup_async() = 0;

        virtual core::Result<std::any> on_method_call_sync(const std::string& method_name,
                                                          const std::vector<std::any>& args) = 0;

    private:
        std::optional<core::Task<core::Result<void>>> async_initialize_task_;
        std::optional<core::Task<core::Result<void>>> async_start_task_;
        std::optional<core::Task<core::Result<void>>> async_stop_task_;
    };

    /**
     * @brief JSON配置支持的插件基类
     */
    class JsonConfigPluginBase : public SimplePluginBase<nlohmann::json> {
    public:
        explicit JsonConfigPluginBase(const PluginMetadata& metadata) 
            : SimplePluginBase<nlohmann::json>(metadata) {}

    protected:
        /**
         * @brief 获取JSON配置值
         */
        template<typename T>
        T get_json_config(const std::string& path, const T& default_value = T{}) const {
            try {
                auto json_ptr = nlohmann::json::json_pointer(path);
                if (get_config().contains(json_ptr)) {
                    return get_config()[json_ptr].get<T>();
                }
            } catch (const std::exception&) {
                // 忽略解析错误，返回默认值
            }
            return default_value;
        }

        /**
         * @brief 设置JSON配置值
         */
        template<typename T>
        void set_json_config(const std::string& path, const T& value) {
            auto& config = const_cast<nlohmann::json&>(get_config());
            auto json_ptr = nlohmann::json::json_pointer(path);
            config[json_ptr] = value;
        }

    private:
        nlohmann::json convert_config(const std::unordered_map<std::string, std::string>& config) override {
            nlohmann::json json_config;
            for (const auto& [key, value] : config) {
                try {
                    // 尝试解析为JSON
                    json_config[key] = nlohmann::json::parse(value);
                } catch (const std::exception&) {
                    // 如果解析失败，作为字符串存储
                    json_config[key] = value;
                }
            }
            return json_config;
        }
    };

} // namespace hushell::plugin