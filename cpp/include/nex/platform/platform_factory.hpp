#pragma once

#include "nex/platform/platform_adapter.hpp"
#include "nex/platform/platform_detector.hpp"
#include <memory>

namespace nex::platform {

    /**
     * @brief 平台工厂类，负责创建合适的平台适配器实例
     */
    class PlatformFactory {
    public:
        /**
         * @brief 创建适合当前平台的适配器实例
         * @return std::unique_ptr<IPlatformAdapter> 平台适配器实例
         * @throws std::runtime_error 如果当前平台不支持
         */
        static std::unique_ptr<IPlatformAdapter> create_adapter();
        
        /**
         * @brief 创建指定平台的适配器实例
         * @param platform_type 指定的平台类型
         * @return std::unique_ptr<IPlatformAdapter> 平台适配器实例
         * @throws std::runtime_error 如果指定平台不支持
         */
        static std::unique_ptr<IPlatformAdapter> create_adapter(PlatformType platform_type);
        
        /**
         * @brief 检查指定平台是否支持
         * @param platform_type 平台类型
         * @return bool 是否支持
         */
        static bool is_platform_supported(PlatformType platform_type) noexcept;
        
        /**
         * @brief 获取支持的平台列表
         * @return std::vector<PlatformType> 支持的平台类型列表
         */
        static std::vector<PlatformType> get_supported_platforms() noexcept;
        
    private:
        PlatformFactory() = default; // 禁止实例化
    };

} // namespace nex::platform