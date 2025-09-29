#pragma once

#include <string>
#include <string_view>

namespace nex::platform {
    
    enum class PlatformType {
        LINUX,
        MACOS,
        WINDOWS,
        UNKNOWN
    };
    
    /**
     * @brief 平台检测器，负责检测当前运行平台并提供平台相关信息
     */
    class PlatformDetector {
    public:
        /**
         * @brief 检测当前平台类型
         * @return PlatformType 检测到的平台类型
         */
        static PlatformType detect_platform() noexcept;
        
        /**
         * @brief 获取平台名称字符串
         * @return std::string 平台名称
         */
        static std::string get_platform_name();
        
        /**
         * @brief 检查是否为类Unix系统
         * @return bool true表示是类Unix系统
         */
        static bool is_unix_like() noexcept;
        
        /**
         * @brief 检查是否支持POSIX标准
         * @return bool true表示支持POSIX
         */
        static bool supports_posix() noexcept;
        
        /**
         * @brief 获取平台架构信息
         * @return std::string 架构信息(x86_64, aarch64等)
         */
        static std::string get_architecture();
        
        /**
         * @brief 获取操作系统版本信息
         * @return std::string 版本信息
         */
        static std::string get_os_version();
        
    private:
        static PlatformType cached_platform_type_;
        static bool platform_detected_;
    };
    
} // namespace nex::platform