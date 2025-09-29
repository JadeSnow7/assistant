"""
现代化CLI主控制器 - 基于Rich/Textual的Claude Code风格界面
"""
import asyncio
import sys
from typing import Optional, Dict, Any, List
from rich.console import Console
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.live import Live
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.prompt import Prompt
from rich.align import Align
from datetime import datetime
import json

from .command_router import CommandRouter
from .session_manager import SessionManager
from .display_engine import DisplayEngine
from .config import CLIConfig
from ..shared.ai_client import EnhancedAIClient


class ModernCLI:
    """现代化CLI主控制器"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.console = Console()
        self.client = EnhancedAIClient(base_url)
        self.session_manager = SessionManager()
        self.command_router = CommandRouter(self)
        self.display_engine = DisplayEngine(self.console)
        self.config = CLIConfig()
        
        # 界面状态
        self.running = True
        self.current_session_id: Optional[str] = None
        
    async def start_interactive_mode(self):
        """启动交互模式"""
        try:
            # 显示欢迎界面
            await self._show_welcome_screen()
            
            # 初始化会话
            await self._initialize_session()
            
            # 进入主循环
            await self._main_loop()
            
        except KeyboardInterrupt:
            await self._handle_exit()
        except Exception as e:
            self.console.print(f"[red]严重错误: {e}[/red]")
            sys.exit(1)
    
    async def _show_welcome_screen(self):
        """显示欢迎界面"""
        welcome_panel = Panel.fit(
            Align.center(
                Text.assemble(
                    ("🤖 ", "blue"),
                    ("AI Assistant CLI v2.0.0", "bold cyan"),
                    "\n",
                    ("智能助手终端界面", "white"),
                    "\n\n",
                    ("输入 ", "dim"),
                    ("/help", "green"),
                    (" 查看命令帮助，", "dim"),
                    ("/exit", "red"), 
                    (" 退出程序", "dim")
                )
            ),
            title="[bold blue]AI Assistant[/bold blue]",
            border_style="blue"
        )
        self.console.print(welcome_panel)
        self.console.print()
    
    async def _initialize_session(self):
        """初始化会话"""
        with self.console.status("[bold green]正在连接服务..."):
            # 初始化会话管理器
            await self.session_manager.initialize()
            
            # 健康检查
            health_result = await self.client.health_check()
            if health_result.get("status") != "healthy":
                self.console.print(
                    f"[yellow]⚠️  服务连接异常: {health_result.get('error', '未知错误')}[/yellow]"
                )
                self.console.print("[dim]部分功能可能不可用[/dim]")
            
            # 创建新会话
            session_info = await self.session_manager.create_session()
            self.current_session_id = session_info.get("session_id")
            
        # 显示会话信息
        status_text = Text.assemble(
            ("📍 会话: ", "white"),
            (f"[{self.current_session_id[:8] if self.current_session_id else 'unknown'}]", "cyan"),
            (" | 🔗 状态: ", "white"),
            ("已连接" if health_result.get("status") == "healthy" else "连接异常", 
             "green" if health_result.get("status") == "healthy" else "yellow"),
            (" | ⚡ 模型: ", "white"),
            ("自动选择", "blue")
        )
        
        info_panel = Panel(
            Align.center(status_text),
            border_style="dim"
        )
        self.console.print(info_panel)
        self.console.print()
    
    async def _main_loop(self):
        """主交互循环"""
        while self.running:
            try:
                # 显示提示符
                session_prefix = f"[{self.current_session_id[:8]}]" if self.current_session_id else "[new]"
                
                # 获取用户输入
                user_input = Prompt.ask(
                    f"[cyan]{session_prefix}[/cyan] [bold]>[/bold]",
                    console=self.console
                ).strip()
                
                if not user_input:
                    continue
                
                # 处理用户输入
                await self.process_user_input(user_input)
                
            except KeyboardInterrupt:
                self.console.print("\n[dim]使用 /exit 退出程序[/dim]")
                continue
            except EOFError:
                await self._handle_exit()
                break
            except Exception as e:
                self.console.print(f"[red]处理输入时出错: {e}[/red]")
    
    async def process_user_input(self, input_text: str):
        """处理用户输入"""
        # 显示用户消息
        self.display_engine.show_user_message(input_text)
        
        # 解析并路由命令
        result = await self.command_router.route_command(input_text)
        
        # 显示结果
        if result:
            self.display_engine.show_result(result)
    
    async def _handle_exit(self):
        """处理退出"""
        self.running = False
        
        goodbye_panel = Panel.fit(
            Align.center(
                Text.assemble(
                    ("👋 ", "yellow"),
                    ("再见！感谢使用 AI Assistant", "bold white"),
                    "\n",
                    ("会话已保存，下次见！", "dim")
                )
            ),
            title="[bold yellow]退出[/bold yellow]",
            border_style="yellow"
        )
        self.console.print(goodbye_panel)
        
        # 清理资源
        await self.session_manager.cleanup()
        await self.client.cleanup()


async def main():
    """CLI主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Assistant 现代化CLI")
    parser.add_argument("--url", default="http://localhost:8000", 
                       help="AI Assistant服务地址")
    parser.add_argument("--debug", action="store_true", 
                       help="启用调试模式")
    
    args = parser.parse_args()
    
    # 创建并启动CLI
    cli = ModernCLI(args.url)
    if args.debug:
        cli.config.debug = True
    
    await cli.start_interactive_mode()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 再见！")