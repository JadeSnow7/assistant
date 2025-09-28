#pragma once

#include <string>
#include <vector>
#include <memory>
#include <chrono>

namespace ai_assistant {

// 通用状态码
enum class StatusCode {
    SUCCESS = 0,
    ERROR_INVALID_PARAM = 1,
    ERROR_NOT_FOUND = 2,
    ERROR_NOT_INITIALIZED = 3,
    ERROR_TIMEOUT = 4,
    ERROR_NETWORK = 5,
    ERROR_INTERNAL = 6
};

// 通用结果结构
template<typename T>
struct Result {
    StatusCode status = StatusCode::SUCCESS;
    std::string message;
    T data;
    
    bool is_success() const { return status == StatusCode::SUCCESS; }
    bool is_error() const { return status != StatusCode::SUCCESS; }
};

// 时间戳类型
using Timestamp = std::chrono::system_clock::time_point;

// 通用工具函数
class Utils {
public:
    static std::string get_current_time_string();
    static Timestamp get_current_timestamp();
    static std::string format_timestamp(const Timestamp& ts);
    static std::vector<std::string> split_string(const std::string& str, char delimiter);
    static std::string join_strings(const std::vector<std::string>& strs, const std::string& delimiter);
    static std::string to_lower(const std::string& str);
    static std::string to_upper(const std::string& str);
    static bool starts_with(const std::string& str, const std::string& prefix);
    static bool ends_with(const std::string& str, const std::string& suffix);
};

// 日志级别
enum class LogLevel {
    DEBUG = 0,
    INFO = 1,
    WARNING = 2,
    ERROR = 3,
    CRITICAL = 4
};

// 简单日志类
class Logger {
public:
    static void set_level(LogLevel level);
    static void log(LogLevel level, const std::string& message);
    static void debug(const std::string& message);
    static void info(const std::string& message);
    static void warning(const std::string& message);
    static void error(const std::string& message);
    static void critical(const std::string& message);

private:
    static LogLevel current_level_;
    static std::string level_to_string(LogLevel level);
};

} // namespace ai_assistant