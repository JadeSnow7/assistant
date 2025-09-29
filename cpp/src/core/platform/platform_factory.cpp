#include "nex/platform/platform_factory.hpp"
#include "nex/platform/unix_platform_adapter.hpp"
#include <stdexcept>

// 当实现Windows适配器时取消注释
// #include "nex/platform/windows_platform_adapter.hpp"

namespace nex::platform {

    std::unique_ptr<IPlatformAdapter> PlatformFactory::create_adapter() {
        return create_adapter(PlatformDetector::detect_platform());
    }

    std::unique_ptr<IPlatformAdapter> PlatformFactory::create_adapter(PlatformType platform_type) {
        switch (platform_type) {
            case PlatformType::LINUX:
            case PlatformType::MACOS:
                return std::make_unique<unix::UnixPlatformAdapter>();
                
            case PlatformType::WINDOWS:
                // TODO: 实现Windows适配器
                // return std::make_unique<windows::WindowsPlatformAdapter>();
                throw std::runtime_error("Windows平台适配器尚未实现");
                
            case PlatformType::UNKNOWN:
            default:
                throw std::runtime_error("不支持的平台类型: " + 
                                       std::to_string(static_cast<int>(platform_type)));
        }
    }

    bool PlatformFactory::is_platform_supported(PlatformType platform_type) noexcept {
        switch (platform_type) {
            case PlatformType::LINUX:
            case PlatformType::MACOS:
                return true;
                
            case PlatformType::WINDOWS:
                return false; // TODO: 当Windows适配器实现后改为true
                
            case PlatformType::UNKNOWN:
            default:
                return false;
        }
    }

    std::vector<PlatformType> PlatformFactory::get_supported_platforms() noexcept {
        std::vector<PlatformType> supported_platforms;
        
        // 检查每个平台类型并添加支持的平台
        for (auto platform : {PlatformType::LINUX, PlatformType::MACOS, PlatformType::WINDOWS}) {
            if (is_platform_supported(platform)) {
                supported_platforms.push_back(platform);
            }
        }
        
        return supported_platforms;
    }

} // namespace nex::platform