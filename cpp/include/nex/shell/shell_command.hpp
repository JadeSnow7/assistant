#pragma once

#include <string>
#include <vector>
#include <map>
#include <filesystem>
#include <chrono>
#include <optional>

namespace nex::shell {

    /**
     * @brief Shell命令执行结果
     */
    struct CommandResult {
        int exit_code = 0;
        std::string stdout_output;
        std::string stderr_output;
        std::chrono::milliseconds execution_time{0};
        bool success = false;
    };

    /**
     * @brief 跨平台Shell命令抽象
     */
    class ShellCommand {
    public:
        std::string command;
        std::vector<std::string> args;
        std::map<std::string, std::string> environment;
        std::filesystem::path working_directory;
        std::chrono::milliseconds timeout{30000}; // 默认30秒超时
        bool redirect_stderr_to_stdout = false;
        
        ShellCommand() = default;
        explicit ShellCommand(const std::string& cmd) : command(cmd) {}
        
        // ========== 常用命令的平台无关构建方法 ==========
        
        /**
         * @brief 创建列出目录内容的命令
         * @param path 目录路径
         * @param show_hidden 是否显示隐藏文件
         * @param long_format 是否使用详细格式
         * @return ShellCommand 构建的命令
         */
        static ShellCommand create_list_directory(
            const std::filesystem::path& path = ".",
            bool show_hidden = false,
            bool long_format = true
        );
        
        /**
         * @brief 创建显示进程列表的命令
         * @param show_all_users 是否显示所有用户的进程
         * @param detailed 是否显示详细信息
         * @return ShellCommand 构建的命令
         */
        static ShellCommand create_process_list(
            bool show_all_users = true,
            bool detailed = true
        );
        
        /**
         * @brief 创建查找文件的命令
         * @param search_path 搜索路径
         * @param pattern 文件名模式
         * @param type 文件类型（f-文件，d-目录）
         * @return ShellCommand 构建的命令
         */
        static ShellCommand create_find_files(
            const std::filesystem::path& search_path,
            const std::string& pattern,
            const std::string& type = ""
        );
        
        /**
         * @brief 创建查看文件内容的命令
         * @param file_path 文件路径
         * @param lines 显示行数（-1表示全部）
         * @param from_end 是否从文件末尾开始
         * @return ShellCommand 构建的命令
         */
        static ShellCommand create_view_file(
            const std::filesystem::path& file_path,
            int lines = -1,
            bool from_end = false
        );
        
        /**
         * @brief 创建文本搜索命令
         * @param pattern 搜索模式
         * @param file_path 文件路径
         * @param case_sensitive 是否区分大小写
         * @param line_numbers 是否显示行号
         * @return ShellCommand 构建的命令
         */
        static ShellCommand create_text_search(
            const std::string& pattern,
            const std::filesystem::path& file_path,
            bool case_sensitive = true,
            bool line_numbers = true
        );
        
        /**
         * @brief 创建系统信息查询命令
         * @param info_type 信息类型（memory, cpu, disk等）
         * @return ShellCommand 构建的命令
         */
        static ShellCommand create_system_info(const std::string& info_type);
        
        /**
         * @brief 创建网络相关命令
         * @param operation 操作类型（ping, netstat, ifconfig等）
         * @param target 目标（IP地址、端口等）
         * @return ShellCommand 构建的命令
         */
        static ShellCommand create_network_command(
            const std::string& operation,
            const std::string& target = ""
        );
        
        // ========== 构建器模式方法 ==========
        
        ShellCommand& with_args(const std::vector<std::string>& arguments) {
            args = arguments;
            return *this;
        }
        
        ShellCommand& add_arg(const std::string& arg) {
            args.push_back(arg);
            return *this;
        }
        
        ShellCommand& in_directory(const std::filesystem::path& dir) {
            working_directory = dir;
            return *this;
        }
        
        ShellCommand& with_timeout(std::chrono::milliseconds ms) {
            timeout = ms;
            return *this;
        }
        
        ShellCommand& with_env(const std::string& key, const std::string& value) {
            environment[key] = value;
            return *this;
        }
        
        ShellCommand& merge_stderr() {
            redirect_stderr_to_stdout = true;
            return *this;
        }
        
        /**
         * @brief 构建完整的命令行字符串
         * @return std::string 可执行的命令行
         */
        std::string build_command_line() const;
        
        /**
         * @brief 验证命令是否有效
         * @return bool 命令是否有效
         */
        bool is_valid() const;
    };

} // namespace nex::shell