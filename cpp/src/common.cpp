#include "../include/common.hpp"
#include <iostream>
#include <sstream>
#include <iomanip>
#include <algorithm>
#include <mutex>

namespace ai_assistant {

// Logger静态成员初始化
LogLevel Logger::current_level_ = LogLevel::INFO;

// Utils工具函数实现
std::string Utils::get_current_time_string() {
    auto now = std::chrono::system_clock::now();
    return format_timestamp(now);
}

Timestamp Utils::get_current_timestamp() {
    return std::chrono::system_clock::now();
}

std::string Utils::format_timestamp(const Timestamp& ts) {
    auto time_t = std::chrono::system_clock::to_time_t(ts);
    auto tm = *std::localtime(&time_t);
    
    std::ostringstream oss;
    oss << std::put_time(&tm, "%Y-%m-%d %H:%M:%S");
    return oss.str();
}

std::vector<std::string> Utils::split_string(const std::string& str, char delimiter) {
    std::vector<std::string> tokens;
    std::stringstream ss(str);
    std::string token;
    
    while (std::getline(ss, token, delimiter)) {
        if (!token.empty()) {
            tokens.push_back(token);
        }
    }
    
    return tokens;
}

std::string Utils::join_strings(const std::vector<std::string>& strs, const std::string& delimiter) {
    if (strs.empty()) {
        return "";
    }
    
    std::ostringstream oss;
    for (size_t i = 0; i < strs.size(); ++i) {
        if (i > 0) {
            oss << delimiter;
        }
        oss << strs[i];
    }
    
    return oss.str();
}

std::string Utils::to_lower(const std::string& str) {
    std::string result = str;
    std::transform(result.begin(), result.end(), result.begin(), 
                   [](unsigned char c) { return std::tolower(c); });
    return result;
}

std::string Utils::to_upper(const std::string& str) {
    std::string result = str;
    std::transform(result.begin(), result.end(), result.begin(), 
                   [](unsigned char c) { return std::toupper(c); });
    return result;
}

bool Utils::starts_with(const std::string& str, const std::string& prefix) {
    if (prefix.length() > str.length()) {
        return false;
    }
    return str.substr(0, prefix.length()) == prefix;
}

bool Utils::ends_with(const std::string& str, const std::string& suffix) {
    if (suffix.length() > str.length()) {
        return false;
    }
    return str.substr(str.length() - suffix.length()) == suffix;
}

// Logger实现
void Logger::set_level(LogLevel level) {
    current_level_ = level;
}

void Logger::log(LogLevel level, const std::string& message) {
    if (level < current_level_) {
        return;
    }
    
    static std::mutex log_mutex;
    std::lock_guard<std::mutex> lock(log_mutex);
    
    std::string timestamp = Utils::get_current_time_string();
    std::string level_str = level_to_string(level);
    
    std::cout << "[" << timestamp << "] [" << level_str << "] " << message << std::endl;
}

void Logger::debug(const std::string& message) {
    log(LogLevel::DEBUG, message);
}

void Logger::info(const std::string& message) {
    log(LogLevel::INFO, message);
}

void Logger::warning(const std::string& message) {
    log(LogLevel::WARNING, message);
}

void Logger::error(const std::string& message) {
    log(LogLevel::ERROR, message);
}

void Logger::critical(const std::string& message) {
    log(LogLevel::CRITICAL, message);
}

std::string Logger::level_to_string(LogLevel level) {
    switch (level) {
        case LogLevel::DEBUG:
            return "DEBUG";
        case LogLevel::INFO:
            return "INFO";
        case LogLevel::WARNING:
            return "WARN";
        case LogLevel::ERROR:
            return "ERROR";
        case LogLevel::CRITICAL:
            return "CRIT";
        default:
            return "UNKNOWN";
    }
}

} // namespace ai_assistant