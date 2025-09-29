#pragma once

#include <concepts>
#include <string>
#include <vector>
#include <memory>
#include <future>
#include <chrono>

namespace nex::concepts {

    /**
     * @brief 推理请求概念
     */
    template<typename T>
    concept InferenceRequestLike = requires(T request) {
        { request.model_id } -> std::convertible_to<std::string>;
        { request.input } -> std::convertible_to<std::string>;
        { request.max_tokens } -> std::convertible_to<int>;
        { request.temperature } -> std::convertible_to<float>;
    };

    /**
     * @brief 推理结果概念
     */
    template<typename T>
    concept InferenceResultLike = requires(T result) {
        { result.output } -> std::convertible_to<std::string>;
        { result.success } -> std::convertible_to<bool>;
        { result.error_message } -> std::convertible_to<std::string>;
        { result.inference_time_ms } -> std::convertible_to<std::chrono::milliseconds>;
    };

    /**
     * @brief 模型提供商概念
     */
    template<typename T>
    concept ModelProvider = requires(T provider) {
        // 基本属性
        { provider.get_name() } -> std::convertible_to<std::string>;
        { provider.get_version() } -> std::convertible_to<std::string>;
        { provider.is_available() } -> std::convertible_to<bool>;
        
        // 生命周期管理
        { provider.initialize() } -> std::convertible_to<bool>;
        { provider.shutdown() } -> std::convertible_to<void>;
        
        // 模型信息
        { provider.get_supported_models() } -> std::convertible_to<std::vector<std::string>>;
        { provider.is_model_loaded(std::string{}) } -> std::convertible_to<bool>;
    };

    /**
     * @brief 异步模型提供商概念（支持协程）
     */
    template<typename T>
    concept AsyncModelProvider = ModelProvider<T> && requires(T provider) {
        // 协程接口需要特殊处理，这里简化为future接口
        typename T::inference_awaitable;
    };

    /**
     * @brief 内存分配器概念
     */
    template<typename T>
    concept MemoryAllocator = requires(T allocator, size_t size) {
        { allocator.allocate(size) } -> std::convertible_to<void*>;
        { allocator.deallocate(std::declval<void*>(), size) } -> std::convertible_to<void>;
        { allocator.get_allocated_size() } -> std::convertible_to<size_t>;
    };

    /**
     * @brief 插件概念
     */
    template<typename T>
    concept Plugin = requires(T plugin) {
        { plugin.get_name() } -> std::convertible_to<std::string>;
        { plugin.get_version() } -> std::convertible_to<std::string>;
        { plugin.get_description() } -> std::convertible_to<std::string>;
        { plugin.initialize() } -> std::convertible_to<bool>;
        { plugin.shutdown() } -> std::convertible_to<void>;
        { plugin.is_compatible(std::string{}) } -> std::convertible_to<bool>;
    };

    /**
     * @brief 系统监控器概念
     */
    template<typename T>
    concept SystemMonitor = requires(T monitor) {
        { monitor.start_monitoring() } -> std::convertible_to<bool>;
        { monitor.stop_monitoring() } -> std::convertible_to<void>;
        { monitor.is_monitoring() } -> std::convertible_to<bool>;
        { monitor.get_cpu_usage() } -> std::convertible_to<double>;
        { monitor.get_memory_usage() } -> std::convertible_to<double>;
    };

    /**
     * @brief 序列化器概念
     */
    template<typename T>
    concept Serializable = requires(T obj, const std::string& data) {
        { obj.serialize() } -> std::convertible_to<std::string>;
        { T::deserialize(data) } -> std::convertible_to<T>;
    };

    /**
     * @brief 日志记录器概念
     */
    template<typename T>
    concept Logger = requires(T logger, const std::string& message) {
        { logger.info(message) } -> std::convertible_to<void>;
        { logger.warning(message) } -> std::convertible_to<void>;
        { logger.error(message) } -> std::convertible_to<void>;
        { logger.debug(message) } -> std::convertible_to<void>;
    };

    /**
     * @brief 缓存概念
     */
    template<typename T, typename K, typename V>
    concept Cache = requires(T cache, K key, V value) {
        { cache.get(key) } -> std::convertible_to<std::optional<V>>;
        { cache.put(key, value) } -> std::convertible_to<void>;
        { cache.contains(key) } -> std::convertible_to<bool>;
        { cache.remove(key) } -> std::convertible_to<bool>;
        { cache.clear() } -> std::convertible_to<void>;
        { cache.size() } -> std::convertible_to<size_t>;
    };

    /**
     * @brief 配置管理器概念
     */
    template<typename T>
    concept ConfigManager = requires(T config, const std::string& key, const std::string& value) {
        { config.get_string(key) } -> std::convertible_to<std::optional<std::string>>;
        { config.get_int(key) } -> std::convertible_to<std::optional<int>>;
        { config.get_double(key) } -> std::convertible_to<std::optional<double>>;
        { config.get_bool(key) } -> std::convertible_to<std::optional<bool>>;
        { config.set(key, value) } -> std::convertible_to<void>;
        { config.has(key) } -> std::convertible_to<bool>;
        { config.save() } -> std::convertible_to<bool>;
        { config.load() } -> std::convertible_to<bool>;
    };

} // namespace nex::concepts