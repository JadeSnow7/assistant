#include "nex/shell/shell_command.hpp"
#include "nex/platform/platform_detector.hpp"
#include <sstream>
#include <algorithm>

namespace nex::shell {

    ShellCommand ShellCommand::create_list_directory(
        const std::filesystem::path& path,
        bool show_hidden,
        bool long_format
    ) {
        ShellCommand cmd;
        
        #ifdef _WIN32
            cmd.command = "dir";
            if (long_format) {
                cmd.args.push_back("/Q"); // 显示所有者
            }
            cmd.args.push_back(path.string());
        #else
            cmd.command = "ls";
            std::string options = "-";
            if (long_format) options += "l";
            if (show_hidden) options += "a";
            
            if (options.length() > 1) {
                cmd.args.push_back(options);
            }
            cmd.args.push_back(path.string());
        #endif
        
        return cmd;
    }

    ShellCommand ShellCommand::create_process_list(bool show_all_users, bool detailed) {
        ShellCommand cmd;
        
        #ifdef _WIN32
            cmd.command = "tasklist";
            if (detailed) {
                cmd.args.push_back("/FO");
                cmd.args.push_back("TABLE");
                cmd.args.push_back("/V"); // 详细信息
            }
        #else
            cmd.command = "ps";
            if (show_all_users && detailed) {
                cmd.args.push_back("aux");
            } else if (show_all_users) {
                cmd.args.push_back("ax");
            } else if (detailed) {
                cmd.args.push_back("ux");
            } else {
                cmd.args.push_back("x");
            }
        #endif
        
        return cmd;
    }

    ShellCommand ShellCommand::create_find_files(
        const std::filesystem::path& search_path,
        const std::string& pattern,
        const std::string& type
    ) {
        ShellCommand cmd;
        
        #ifdef _WIN32
            cmd.command = "dir";
            cmd.args.push_back("/S"); // 递归搜索
            cmd.args.push_back("/B"); // 仅显示文件名
            cmd.args.push_back((search_path / pattern).string());
        #else
            cmd.command = "find";
            cmd.args.push_back(search_path.string());
            
            if (!type.empty()) {
                cmd.args.push_back("-type");
                cmd.args.push_back(type);
            }
            
            cmd.args.push_back("-name");
            cmd.args.push_back(pattern);
        #endif
        
        return cmd;
    }

    ShellCommand ShellCommand::create_view_file(
        const std::filesystem::path& file_path,
        int lines,
        bool from_end
    ) {
        ShellCommand cmd;
        
        #ifdef _WIN32
            if (lines > 0) {
                // Windows没有直接的head/tail命令，使用PowerShell
                cmd.command = "powershell";
                std::string ps_cmd;
                if (from_end) {
                    ps_cmd = "Get-Content '" + file_path.string() + "' | Select-Object -Last " + std::to_string(lines);
                } else {
                    ps_cmd = "Get-Content '" + file_path.string() + "' | Select-Object -First " + std::to_string(lines);
                }
                cmd.args.push_back("-Command");
                cmd.args.push_back(ps_cmd);
            } else {
                cmd.command = "type";
                cmd.args.push_back(file_path.string());
            }
        #else
            if (lines > 0) {
                if (from_end) {
                    cmd.command = "tail";
                    cmd.args.push_back("-n");
                    cmd.args.push_back(std::to_string(lines));
                } else {
                    cmd.command = "head";
                    cmd.args.push_back("-n");
                    cmd.args.push_back(std::to_string(lines));
                }
            } else {
                cmd.command = "cat";
            }
            cmd.args.push_back(file_path.string());
        #endif
        
        return cmd;
    }

    ShellCommand ShellCommand::create_text_search(
        const std::string& pattern,
        const std::filesystem::path& file_path,
        bool case_sensitive,
        bool line_numbers
    ) {
        ShellCommand cmd;
        
        #ifdef _WIN32
            cmd.command = "findstr";
            if (!case_sensitive) {
                cmd.args.push_back("/I");
            }
            if (line_numbers) {
                cmd.args.push_back("/N");
            }
            cmd.args.push_back(pattern);
            cmd.args.push_back(file_path.string());
        #else
            cmd.command = "grep";
            if (!case_sensitive) {
                cmd.args.push_back("-i");
            }
            if (line_numbers) {
                cmd.args.push_back("-n");
            }
            cmd.args.push_back(pattern);
            cmd.args.push_back(file_path.string());
        #endif
        
        return cmd;
    }

    ShellCommand ShellCommand::create_system_info(const std::string& info_type) {
        ShellCommand cmd;
        
        #ifdef _WIN32
            if (info_type == "memory") {
                cmd.command = "wmic";
                cmd.args = {"OS", "get", "TotalVisibleMemorySize,FreePhysicalMemory", "/format:list"};
            } else if (info_type == "cpu") {
                cmd.command = "wmic";
                cmd.args = {"cpu", "get", "Name,NumberOfCores,NumberOfLogicalProcessors", "/format:list"};
            } else if (info_type == "disk") {
                cmd.command = "wmic";
                cmd.args = {"logicaldisk", "get", "Size,FreeSpace,Caption", "/format:list"};
            } else {
                cmd.command = "systeminfo";
            }
        #else
            if (info_type == "memory") {
                cmd.command = "free";
                cmd.args.push_back("-h");
            } else if (info_type == "cpu") {
                cmd.command = "lscpu";
            } else if (info_type == "disk") {
                cmd.command = "df";
                cmd.args.push_back("-h");
            } else {
                cmd.command = "uname";
                cmd.args.push_back("-a");
            }
        #endif
        
        return cmd;
    }

    ShellCommand ShellCommand::create_network_command(
        const std::string& operation,
        const std::string& target
    ) {
        ShellCommand cmd;
        
        if (operation == "ping") {
            cmd.command = "ping";
            #ifdef _WIN32
                cmd.args = {"-n", "4", target}; // Windows: 4次ping
            #else
                cmd.args = {"-c", "4", target}; // Unix: 4次ping
            #endif
        } else if (operation == "netstat") {
            cmd.command = "netstat";
            #ifdef _WIN32
                cmd.args = {"-an"};
            #else
                cmd.args = {"-tuln"};
            #endif
        } else if (operation == "ifconfig" || operation == "interfaces") {
            #ifdef _WIN32
                cmd.command = "ipconfig";
                cmd.args = {"/all"};
            #else
                // 优先使用ip命令，fallback到ifconfig
                cmd.command = "ip";
                cmd.args = {"addr", "show"};
            #endif
        } else if (operation == "route") {
            #ifdef _WIN32
                cmd.command = "route";
                cmd.args = {"print"};
            #else
                cmd.command = "ip";
                cmd.args = {"route", "show"};
            #endif
        }
        
        return cmd;
    }

    std::string ShellCommand::build_command_line() const {
        std::ostringstream oss;
        
        oss << command;
        
        for (const auto& arg : args) {
            oss << " ";
            // 如果参数包含空格，需要用引号包围
            if (arg.find(' ') != std::string::npos) {
                oss << "\"" << arg << "\"";
            } else {
                oss << arg;
            }
        }
        
        return oss.str();
    }

    bool ShellCommand::is_valid() const {
        return !command.empty();
    }

} // namespace nex::shell