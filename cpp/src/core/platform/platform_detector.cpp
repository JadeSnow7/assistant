#include "nex/platform/platform_detector.hpp"
#include <thread>

#ifdef _WIN32
    #include <windows.h>
    #include <versionhelpers.h>
#elif defined(__APPLE__)
    #include <sys/utsname.h>
    #include <mach/mach.h>
#else
    #include <sys/utsname.h>
    #include <unistd.h>
#endif

namespace nex::platform {

    // 静态成员初始化
    PlatformType PlatformDetector::cached_platform_type_ = PlatformType::UNKNOWN;
    bool PlatformDetector::platform_detected_ = false;

    PlatformType PlatformDetector::detect_platform() noexcept {
        if (platform_detected_) {
            return cached_platform_type_;
        }

        try {
            #ifdef _WIN32
                cached_platform_type_ = PlatformType::WINDOWS;
            #elif defined(__APPLE__)
                cached_platform_type_ = PlatformType::MACOS;
            #elif defined(__linux__)
                cached_platform_type_ = PlatformType::LINUX;
            #else
                cached_platform_type_ = PlatformType::UNKNOWN;
            #endif
            
            platform_detected_ = true;
            return cached_platform_type_;
        } catch (...) {
            return PlatformType::UNKNOWN;
        }
    }

    std::string PlatformDetector::get_platform_name() {
        const auto platform = detect_platform();
        
        switch (platform) {
            case PlatformType::LINUX:
                return "Linux";
            case PlatformType::MACOS:
                return "macOS";
            case PlatformType::WINDOWS:
                return "Windows";
            default:
                return "Unknown";
        }
    }

    bool PlatformDetector::is_unix_like() noexcept {
        const auto platform = detect_platform();
        return platform == PlatformType::LINUX || platform == PlatformType::MACOS;
    }

    bool PlatformDetector::supports_posix() noexcept {
        #ifdef _POSIX_VERSION
            return is_unix_like();
        #else
            return false;
        #endif
    }

    std::string PlatformDetector::get_architecture() {
        #ifdef _WIN32
            SYSTEM_INFO sys_info;
            GetSystemInfo(&sys_info);
            
            switch (sys_info.wProcessorArchitecture) {
                case PROCESSOR_ARCHITECTURE_AMD64:
                    return "x86_64";
                case PROCESSOR_ARCHITECTURE_ARM64:
                    return "aarch64";
                case PROCESSOR_ARCHITECTURE_INTEL:
                    return "x86";
                case PROCESSOR_ARCHITECTURE_ARM:
                    return "arm";
                default:
                    return "unknown";
            }
        #else
            struct utsname sys_info;
            if (uname(&sys_info) == 0) {
                return std::string(sys_info.machine);
            }
            return "unknown";
        #endif
    }

    std::string PlatformDetector::get_os_version() {
        #ifdef _WIN32
            // Windows版本检测
            if (IsWindows10OrGreater()) {
                return "Windows 10+";
            } else if (IsWindows8Point1OrGreater()) {
                return "Windows 8.1";
            } else if (IsWindows8OrGreater()) {
                return "Windows 8";
            } else if (IsWindows7OrGreater()) {
                return "Windows 7";
            } else {
                return "Windows (Unknown Version)";
            }
        #else
            struct utsname sys_info;
            if (uname(&sys_info) == 0) {
                return std::string(sys_info.sysname) + " " + std::string(sys_info.release);
            }
            return "Unknown Unix-like System";
        #endif
    }

} // namespace nex::platform