"""
命令路由系统 - 解析和路由用户命令
"""
import re
import asyncio
import subprocess
from typing import Dict, List, Optional, Any, Callable
from abc import ABC, abstractmethod


class CommandResult:
    """命令执行结果"""
    
    def __init__(self, success: bool = True, content: str = "", 
                 error: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        self.success = success
        self.content = content
        self.error = error
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "success": self.success,
            "content": self.content
        }
        if self.error:
            result["error"] = self.error
        if self.metadata:
            result.update(self.metadata)
        return result


class CommandBase(ABC):
    """命令基类"""
    
    def __init__(self, name: str, description: str, aliases: Optional[List[str]] = None):
        self.name = name
        self.description = description
        self.aliases = aliases or []
    
    @abstractmethod
    async def execute(self, args: List[str], cli_controller) -> CommandResult:
        """执行命令"""
        pass
    
    def validate(self, args: List[str]) -> bool:
        """验证参数"""
        return True
    
    def get_help(self) -> str:
        """获取帮助信息"""
        return self.description


class ChatCommand(CommandBase):
    """聊天命令处理器"""
    
    def __init__(self):
        super().__init__(
            "chat", 
            "发送聊天消息", 
            ["c"]
        )
    
    async def execute(self, args: List[str], cli_controller) -> CommandResult:
        """执行聊天命令"""
        if not args:
            return CommandResult(False, error="请输入消息内容")
        
        message = " ".join(args)
        
        try:
            # 调用AI客户端进行聊天
            result = await cli_controller.client.chat(
                message, 
                session_id=cli_controller.current_session_id
            )
            
            if "error" in result:
                return CommandResult(False, error=result["error"])
            
            # 更新会话ID
            if not cli_controller.current_session_id and result.get("session_id"):
                cli_controller.current_session_id = result["session_id"]
            
            return CommandResult(
                True,
                content=result.get("content", "无响应"),
                metadata={
                    "model_used": result.get("model_used"),
                    "reasoning": result.get("reasoning"),
                    "response_time": result.get("response_time"),
                    "cost": result.get("cost"),
                    "plugins_used": result.get("plugins_used")
                }
            )
            
        except Exception as e:
            return CommandResult(False, error=f"聊天请求失败: {str(e)}")


class StreamCommand(CommandBase):
    """流式聊天命令处理器"""
    
    def __init__(self):
        super().__init__(
            "stream", 
            "流式聊天，实时显示AI响应", 
            ["s"]
        )
    
    async def execute(self, args: List[str], cli_controller) -> CommandResult:
        """执行流式聊天命令"""
        if not args:
            return CommandResult(False, error="请输入消息内容")
        
        message = " ".join(args)
        
        try:
            # 开始流式显示
            streaming_display = cli_controller.display_engine.show_streaming_response()
            
            full_response = ""
            metadata = {}
            
            # 获取流式响应
            async for chunk in cli_controller.client.chat_stream(
                message,
                session_id=cli_controller.current_session_id
            ):
                if "error" in chunk:
                    streaming_display.cancel(f"错误: {chunk['error']}")
                    return CommandResult(False, error=chunk["error"])
                
                content = chunk.get("content", "")
                full_response += content
                streaming_display.add_chunk(content, chunk)
                
                # 收集元数据
                for key in ["model_used", "response_time", "cost", "session_id", "plugins_used"]:
                    if key in chunk:
                        metadata[key] = chunk[key]
            
            # 完成流式显示
            streaming_display.finish(metadata)
            
            # 更新会话ID
            if not cli_controller.current_session_id and metadata.get("session_id"):
                cli_controller.current_session_id = metadata["session_id"]
            
            return CommandResult(True, content=full_response, metadata=metadata)
            
        except Exception as e:
            return CommandResult(False, error=f"流式聊天请求失败: {str(e)}")


class SystemCommand(CommandBase):
    """系统命令处理器"""
    
    def __init__(self):
        super().__init__(
            "status", 
            "查看系统状态", 
            ["stat"]
        )
    
    async def execute(self, args: List[str], cli_controller) -> CommandResult:
        """执行系统状态查询"""
        try:
            result = await cli_controller.client.get_system_status()
            
            if "error" in result:
                return CommandResult(False, error=result["error"])
            
            # 使用显示引擎显示状态
            cli_controller.display_engine.show_system_status(result)
            
            return CommandResult(True, content="系统状态已显示")
            
        except Exception as e:
            return CommandResult(False, error=f"获取系统状态失败: {str(e)}")


class PluginsCommand(CommandBase):
    """插件命令处理器"""
    
    def __init__(self):
        super().__init__(
            "plugins", 
            "查看插件列表", 
            ["plugin", "p"]
        )
    
    async def execute(self, args: List[str], cli_controller) -> CommandResult:
        """执行插件列表查询"""
        try:
            result = await cli_controller.client.list_plugins()
            
            if "error" in result:
                return CommandResult(False, error=result["error"])
            
            plugins = result.get("plugins", [])
            cli_controller.display_engine.show_plugins_list(plugins)
            
            return CommandResult(True, content=f"插件列表已显示 ({len(plugins)}个)")
            
        except Exception as e:
            return CommandResult(False, error=f"获取插件列表失败: {str(e)}")


class ShellCommand(CommandBase):
    """Shell命令处理器"""
    
    def __init__(self, shell_type: str):
        self.shell_type = shell_type
        super().__init__(
            shell_type, 
            f"执行{shell_type.upper()}命令", 
            []
        )
    
    async def execute(self, args: List[str], cli_controller) -> CommandResult:
        """执行Shell命令"""
        if not args:
            return CommandResult(False, error=f"请输入{self.shell_type}命令")
        
        command = " ".join(args)
        
        try:
            # 执行Shell命令
            process = await asyncio.create_subprocess_exec(
                self.shell_type,
                "-c",
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                output = stdout.decode('utf-8', errors='ignore')
                return CommandResult(
                    True, 
                    content=output,
                    metadata={"command": command, "shell": self.shell_type}
                )
            else:
                error_output = stderr.decode('utf-8', errors='ignore')
                return CommandResult(
                    False, 
                    error=f"命令执行失败: {error_output}",
                    metadata={"command": command, "shell": self.shell_type}
                )
                
        except Exception as e:
            return CommandResult(False, error=f"执行{self.shell_type}命令失败: {str(e)}")


class MetaCommand(CommandBase):
    """元命令处理器"""
    
    def __init__(self, command_type: str):
        self.command_type = command_type
        descriptions = {
            "help": "显示帮助信息",
            "exit": "退出程序",
            "quit": "退出程序", 
            "clear": "清屏"
        }
        super().__init__(
            command_type,
            descriptions.get(command_type, "元命令"),
            []
        )
    
    async def execute(self, args: List[str], cli_controller) -> CommandResult:
        """执行元命令"""
        if self.command_type in ["help"]:
            return await self._handle_help(args, cli_controller)
        elif self.command_type in ["exit", "quit"]:
            return await self._handle_exit(args, cli_controller)
        elif self.command_type == "clear":
            return await self._handle_clear(args, cli_controller)
        else:
            return CommandResult(False, error=f"未知的元命令: {self.command_type}")
    
    async def _handle_help(self, args: List[str], cli_controller) -> CommandResult:
        """处理帮助命令"""
        commands = {
            "/help": "显示此帮助信息",
            "/exit, /quit": "退出程序",
            "/clear": "清屏",
            "/status": "查看系统状态",
            "/plugins": "查看插件列表",
            "/chat <消息>": "发送聊天消息",
            "/stream <消息>": "流式聊天",
            "/bash <命令>": "执行Bash命令",
            "/zsh <命令>": "执行Zsh命令",
            "/fish <命令>": "执行Fish命令",
            "直接输入": "自动识别为聊天消息"
        }
        
        cli_controller.display_engine.show_help(commands)
        return CommandResult(True, content="帮助信息已显示")
    
    async def _handle_exit(self, args: List[str], cli_controller) -> CommandResult:
        """处理退出命令"""
        cli_controller.running = False
        return CommandResult(True, content="正在退出...")
    
    async def _handle_clear(self, args: List[str], cli_controller) -> CommandResult:
        """处理清屏命令"""
        cli_controller.console.clear()
        return CommandResult(True, content="屏幕已清除")


class CommandRouter:
    """命令路由器"""
    
    def __init__(self, cli_controller):
        self.cli_controller = cli_controller
        self.commands: Dict[str, CommandBase] = {}
        self.aliases: Dict[str, str] = {}
        
        # 注册内置命令
        self._register_builtin_commands()
    
    def _register_builtin_commands(self):
        """注册内置命令"""
        # 聊天命令
        chat_cmd = ChatCommand()
        self.register_command(chat_cmd)
        
        # 流式聊天命令
        stream_cmd = StreamCommand()
        self.register_command(stream_cmd)
        
        # 系统命令
        status_cmd = SystemCommand()
        self.register_command(status_cmd)
        
        # 插件命令
        plugins_cmd = PluginsCommand()
        self.register_command(plugins_cmd)
        
        # Shell命令
        for shell in ["bash", "zsh", "fish"]:
            shell_cmd = ShellCommand(shell)
            self.register_command(shell_cmd)
        
        # 元命令
        for meta in ["help", "exit", "quit", "clear"]:
            meta_cmd = MetaCommand(meta)
            self.register_command(meta_cmd)
    
    def register_command(self, command: CommandBase):
        """注册命令"""
        self.commands[command.name] = command
        
        # 注册别名
        for alias in command.aliases:
            self.aliases[alias] = command.name
    
    async def route_command(self, input_text: str) -> Optional[CommandResult]:
        """路由命令"""
        input_text = input_text.strip()
        
        if not input_text:
            return None
        
        # 检查是否为命令（以/开头）
        if input_text.startswith('/'):
            return await self._handle_slash_command(input_text[1:])
        else:
            # 默认为聊天命令
            return await self._handle_default_chat(input_text)
    
    async def _handle_slash_command(self, command_text: str) -> CommandResult:
        """处理斜杠命令"""
        parts = command_text.split()
        if not parts:
            return CommandResult(False, error="空命令")
        
        command_name = parts[0].lower()
        args = parts[1:]
        
        # 解析别名
        if command_name in self.aliases:
            command_name = self.aliases[command_name]
        
        # 查找命令
        if command_name not in self.commands:
            return CommandResult(False, error=f"未知命令: /{command_name}")
        
        command = self.commands[command_name]
        
        # 验证参数
        if not command.validate(args):
            return CommandResult(False, error=f"命令参数无效: /{command_name}")
        
        # 执行命令
        return await command.execute(args, self.cli_controller)
    
    async def _handle_default_chat(self, message: str) -> CommandResult:
        """处理默认聊天"""
        # 默认使用流式聊天
        if self.cli_controller.config.stream_by_default:
            stream_cmd = self.commands["stream"]
            return await stream_cmd.execute([message], self.cli_controller)
        else:
            chat_cmd = self.commands["chat"]
            return await chat_cmd.execute([message], self.cli_controller)
    
    def get_available_commands(self) -> Dict[str, str]:
        """获取可用命令列表"""
        return {cmd.name: cmd.description for cmd in self.commands.values()}