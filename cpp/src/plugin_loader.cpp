#include "../include/plugin_loader.hpp"
#include "../include/common.hpp"
#include <iostream>
#include <dlfcn.h>
#include <filesystem>
#include <fstream>

namespace ai_assistant {

class PluginLoader::Impl {
public:
    Impl() {}
    
    ~Impl() {
        unload_all_plugins();
    }
    
    bool load_plugin(const std::string& plugin_path) {
        try {
            if (loaded_plugins_.find(plugin_path) != loaded_plugins_.end()) {
                Logger::warning("Plugin already loaded: " + plugin_path);
                return true;
            }
            
            // 检查插件文件是否存在
            if (!std::filesystem::exists(plugin_path)) {
                Logger::error("Plugin file not found: " + plugin_path);
                return false;
            }
            
            // 加载动态库
            void* handle = dlopen(plugin_path.c_str(), RTLD_LAZY);
            if (!handle) {
                Logger::error("Failed to load plugin: " + std::string(dlerror()));
                return false;
            }
            
            // 获取插件信息函数
            typedef PluginInfo* (*get_plugin_info_func)();
            get_plugin_info_func get_info = (get_plugin_info_func) dlsym(handle, "get_plugin_info");
            
            if (!get_info) {
                Logger::error("Plugin missing get_plugin_info function: " + plugin_path);
                dlclose(handle);
                return false;
            }
            
            // 获取插件信息
            PluginInfo* info = get_info();
            if (!info) {
                Logger::error("Failed to get plugin info: " + plugin_path);
                dlclose(handle);
                return false;
            }
            
            // 存储插件信息
            LoadedPlugin loaded_plugin;
            loaded_plugin.handle = handle;
            loaded_plugin.info = *info;
            loaded_plugin.path = plugin_path;
            
            loaded_plugins_[plugin_path] = loaded_plugin;
            
            Logger::info("Plugin loaded successfully: " + info->name + " v" + info->version);
            return true;
            
        } catch (const std::exception& e) {
            Logger::error("Exception while loading plugin: " + std::string(e.what()));
            return false;
        }
    }
    
    bool unload_plugin(const std::string& plugin_path) {
        auto it = loaded_plugins_.find(plugin_path);
        if (it == loaded_plugins_.end()) {
            Logger::warning("Plugin not loaded: " + plugin_path);
            return false;
        }
        
        try {
            // 调用插件清理函数（如果存在）
            typedef void (*cleanup_func)();
            cleanup_func cleanup = (cleanup_func) dlsym(it->second.handle, "plugin_cleanup");
            if (cleanup) {
                cleanup();
            }
            
            // 卸载动态库
            if (dlclose(it->second.handle) != 0) {
                Logger::error("Failed to unload plugin: " + std::string(dlerror()));
                return false;
            }
            
            Logger::info("Plugin unloaded: " + it->second.info.name);
            loaded_plugins_.erase(it);
            return true;
            
        } catch (const std::exception& e) {
            Logger::error("Exception while unloading plugin: " + std::string(e.what()));
            return false;
        }
    }
    
    void unload_all_plugins() {
        for (auto& pair : loaded_plugins_) {
            try {
                dlclose(pair.second.handle);
                Logger::debug("Unloaded plugin: " + pair.second.info.name);
            } catch (const std::exception& e) {
                Logger::warning("Error unloading plugin " + pair.second.info.name + ": " + std::string(e.what()));
            }
        }
        loaded_plugins_.clear();
    }
    
    std::vector<PluginInfo> get_loaded_plugins() const {
        std::vector<PluginInfo> plugins;
        for (const auto& pair : loaded_plugins_) {
            plugins.push_back(pair.second.info);
        }
        return plugins;
    }
    
    bool call_plugin_function(const std::string& plugin_path, const std::string& function_name, const std::string& input, std::string& output) {
        auto it = loaded_plugins_.find(plugin_path);
        if (it == loaded_plugins_.end()) {
            Logger::error("Plugin not loaded: " + plugin_path);
            return false;
        }
        
        try {
            // 获取函数指针
            typedef const char* (*plugin_func)(const char*);
            plugin_func func = (plugin_func) dlsym(it->second.handle, function_name.c_str());
            
            if (!func) {
                Logger::error("Function not found in plugin: " + function_name);
                return false;
            }
            
            // 调用函数
            const char* result = func(input.c_str());
            if (result) {
                output = std::string(result);
                return true;
            } else {
                Logger::error("Plugin function returned null");
                return false;
            }
            
        } catch (const std::exception& e) {
            Logger::error("Exception while calling plugin function: " + std::string(e.what()));
            return false;
        }
    }
    
    std::vector<std::string> discover_plugins(const std::string& directory) const {
        std::vector<std::string> plugin_files;
        
        try {
            if (!std::filesystem::exists(directory)) {
                Logger::warning("Plugin directory does not exist: " + directory);
                return plugin_files;
            }
            
            for (const auto& entry : std::filesystem::directory_iterator(directory)) {
                if (entry.is_regular_file()) {
                    std::string path = entry.path().string();
                    
                    // 检查文件扩展名
#ifdef __linux__
                    if (path.ends_with(".so")) {
#elif _WIN32
                    if (path.ends_with(".dll")) {
#elif __APPLE__
                    if (path.ends_with(".dylib")) {
#endif
                        plugin_files.push_back(path);
                    }
                }
            }
            
            Logger::info("Discovered " + std::to_string(plugin_files.size()) + " potential plugins in " + directory);
            
        } catch (const std::exception& e) {
            Logger::error("Error discovering plugins: " + std::string(e.what()));
        }
        
        return plugin_files;
    }
    
    bool validate_plugin(const std::string& plugin_path) const {
        try {
            // 检查文件是否存在且可读
            if (!std::filesystem::exists(plugin_path)) {
                return false;
            }
            
            // 尝试加载但不执行
            void* handle = dlopen(plugin_path.c_str(), RTLD_LAZY | RTLD_NOLOAD);
            if (handle) {
                dlclose(handle);
                return true;
            }
            
            // 检查是否有必需的符号
            handle = dlopen(plugin_path.c_str(), RTLD_LAZY);
            if (!handle) {
                return false;
            }
            
            bool valid = (dlsym(handle, "get_plugin_info") != nullptr);
            dlclose(handle);
            
            return valid;
            
        } catch (const std::exception& e) {
            Logger::debug("Plugin validation failed: " + std::string(e.what()));
            return false;
        }
    }

private:
    struct LoadedPlugin {
        void* handle;
        PluginInfo info;
        std::string path;
    };
    
    std::map<std::string, LoadedPlugin> loaded_plugins_;
};

// PluginLoader公共接口实现
PluginLoader::PluginLoader() : pimpl_(std::make_unique<Impl>()) {}

PluginLoader::~PluginLoader() = default;

bool PluginLoader::load_plugin(const std::string& plugin_path) {
    return pimpl_->load_plugin(plugin_path);
}

bool PluginLoader::unload_plugin(const std::string& plugin_path) {
    return pimpl_->unload_plugin(plugin_path);
}

void PluginLoader::unload_all_plugins() {
    pimpl_->unload_all_plugins();
}

std::vector<PluginInfo> PluginLoader::get_loaded_plugins() const {
    return pimpl_->get_loaded_plugins();
}

bool PluginLoader::call_plugin_function(const std::string& plugin_path, const std::string& function_name, const std::string& input, std::string& output) {
    return pimpl_->call_plugin_function(plugin_path, function_name, input, output);
}

std::vector<std::string> PluginLoader::discover_plugins(const std::string& directory) const {
    return pimpl_->discover_plugins(directory);
}

bool PluginLoader::validate_plugin(const std::string& plugin_path) const {
    return pimpl_->validate_plugin(plugin_path);
}

} // namespace ai_assistant