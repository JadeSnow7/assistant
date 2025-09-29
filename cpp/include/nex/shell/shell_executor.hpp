#pragma once

#include "nex/shell/shell_command.hpp"
#include "nex/platform/platform_adapter.hpp"
#include <memory>
#include <future>
#include <functional>

namespace nex::shell {

    /**
     * @brief Shell命令执行器 - 提供跨平台的命令执行能力
     */
    class ShellExecutor {
    public:
        using ProgressCallback = std::function<void(const std::string&)>;
        using CompletionCallback = std::function<void(const CommandResult&)>;

        /**
         * @brief 构造函数
         * @param platform_adapter 平台适配器实例
         */
        explicit ShellExecutor(std::shared_ptr<platform::IPlatformAdapter> platform_adapter);
        
        ~ShellExecutor() = default;

        // 禁用拷贝，但允许移动
        ShellExecutor(const ShellExecutor&) = delete;
        ShellExecutor& operator=(const ShellExecutor&) = delete;
        ShellExecutor(ShellExecutor&&) = default;
        ShellExecutor& operator=(ShellExecutor&&) = default;

        /**
         * @brief 同步执行命令
         * @param command 要执行的命令
         * @return CommandResult 执行结果
         */
        CommandResult execute(const ShellCommand& command);

        /**
         * @brief 异步执行命令
         * @param command 要执行的命令
         * @return std::future<CommandResult> 异步执行结果
         */
        std::future<CommandResult> execute_async(const ShellCommand& command);

        /**
         * @brief 执行命令并提供进度回调
         * @param command 要执行的命令
         * @param progress_callback 进度回调函数
         * @return CommandResult 执行结果
         */
        CommandResult execute_with_progress(
            const ShellCommand& command,
            ProgressCallback progress_callback
        );

        /**
         * @brief 异步执行命令并在完成时调用回调
         * @param command 要执行的命令
         * @param completion_callback 完成回调函数
         */
        void execute_async_with_callback(
            const ShellCommand& command,
            CompletionCallback completion_callback
        );

        /**
         * @brief 执行命令并实时流式输出
         * @param command 要执行的命令
         * @param output_callback 输出回调函数
         * @return CommandResult 执行结果
         */
        CommandResult execute_streaming(
            const ShellCommand& command,
            std::function<void(const std::string&, bool)> output_callback // bool表示是否为stderr
        );

        /**
         * @brief 批量执行命令
         * @param commands 命令列表
         * @param fail_fast 遇到失败是否立即停止
         * @return std::vector<CommandResult> 所有命令的执行结果
         */
        std::vector<CommandResult> execute_batch(
            const std::vector<ShellCommand>& commands,
            bool fail_fast = false
        );

        /**
         * @brief 管道执行命令（将前一个命令的输出作为后一个命令的输入）
         * @param commands 命令管道
         * @return CommandResult 最终执行结果
         */
        CommandResult execute_pipeline(const std::vector<ShellCommand>& commands);

        /**
         * @brief 检查命令是否存在
         * @param command_name 命令名称
         * @return bool 命令是否存在
         */
        bool command_exists(const std::string& command_name);

        /**
         * @brief 获取命令的完整路径
         * @param command_name 命令名称
         * @return std::optional<std::filesystem::path> 命令路径
         */
        std::optional<std::filesystem::path> which(const std::string& command_name);

        /**
         * @brief 设置默认超时时间
         * @param timeout 超时时间
         */
        void set_default_timeout(std::chrono::milliseconds timeout) {
            default_timeout_ = timeout;
        }

        /**
         * @brief 设置默认工作目录
         * @param directory 工作目录
         */
        void set_default_working_directory(const std::filesystem::path& directory) {
            default_working_directory_ = directory;
        }

        /**
         * @brief 获取最后一次执行的结果
         * @return std::optional<CommandResult> 最后执行结果
         */
        std::optional<CommandResult> get_last_result() const {
            return last_result_;
        }

    private:
        std::shared_ptr<platform::IPlatformAdapter> platform_adapter_;
        std::chrono::milliseconds default_timeout_{30000};
        std::filesystem::path default_working_directory_;
        std::optional<CommandResult> last_result_;

        // 私有执行方法
        CommandResult execute_internal(
            const ShellCommand& command,
            bool capture_output = true,
            ProgressCallback progress_callback = nullptr,
            std::function<void(const std::string&, bool)> output_callback = nullptr
        );

        // 辅助方法
        std::string prepare_environment(const std::map<std::string, std::string>& env);
        void apply_command_defaults(ShellCommand& command);
        bool is_timeout_exceeded(
            const std::chrono::steady_clock::time_point& start_time,
            std::chrono::milliseconds timeout
        );
    };

    /**
     * @brief Shell执行器工厂 - 便于创建执行器实例
     */
    class ShellExecutorFactory {
    public:
        /**
         * @brief 创建默认的Shell执行器
         * @return std::unique_ptr<ShellExecutor> 执行器实例
         */
        static std::unique_ptr<ShellExecutor> create_default();

        /**
         * @brief 使用指定平台适配器创建Shell执行器
         * @param platform_adapter 平台适配器
         * @return std::unique_ptr<ShellExecutor> 执行器实例
         */
        static std::unique_ptr<ShellExecutor> create_with_adapter(
            std::shared_ptr<platform::IPlatformAdapter> platform_adapter
        );
    };

} // namespace nex::shell