"""
显示引擎 - 负责所有UI渲染和格式化
"""
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.live import Live
from rich.align import Align
from rich.layout import Layout
from rich.columns import Columns
from .streaming_display import AdvancedStreamingDisplay, ProgressTracker


class DisplayEngine:
    """显示引擎类"""
    
    def __init__(self, console: Console):
        self.console = console
        self.live_display: Optional[Live] = None
        
    def show_user_message(self, message: str, timestamp: Optional[datetime] = None):
        """显示用户消息"""
        if timestamp is None:
            timestamp = datetime.now()
        
        time_str = timestamp.strftime("%H:%M") if timestamp else ""
        
        user_text = Text.assemble(
            ("👤 用户", "bold blue"),
            (f" ({time_str})" if time_str else "", "dim"),
            "\n",
            (message, "white")
        )
        
        user_panel = Panel(
            user_text,
            border_style="blue",
            padding=(0, 1)
        )
        
        self.console.print(user_panel)
        self.console.print()
    
    def show_ai_response(self, content: str, metadata: Optional[Dict[str, Any]] = None):
        """显示AI响应"""
        timestamp = datetime.now().strftime("%H:%M")
        
        # AI标题
        ai_title = Text.assemble(
            ("🤖 AI助手", "bold green"),
            (f" ({timestamp})", "dim")
        )
        
        # 如果有模型信息，添加到标题
        if metadata:
            model_info = self._format_model_info(metadata)
            if model_info:
                ai_title.append(f" {model_info}", style="cyan")
        
        # 处理内容格式
        if self._is_code_block(content):
            # 代码块
            content_display = Syntax(content, "python", theme="monokai", line_numbers=True)
        elif self._is_markdown(content):
            # Markdown内容
            content_display = Markdown(content)
        else:
            # 普通文本
            content_display = Text(content, style="white")
        
        ai_panel = Panel(
            content_display,
            title=ai_title,
            border_style="green",
            padding=(0, 1)
        )
        
        self.console.print(ai_panel)
        
        # 显示性能信息
        if metadata and metadata.get("show_stats", True):
            self._show_performance_stats(metadata)
        
        self.console.print()
    
    def show_streaming_response(self, initial_metadata: Optional[Dict[str, Any]] = None):
        """开始流式响应显示"""
        return AdvancedStreamingDisplay(self.console, "AI助手").start(initial_metadata)
    
    def show_system_status(self, status_data: Dict[str, Any]):
        """显示系统状态"""
        # 创建状态表格
        status_table = Table(title="📊 系统状态", show_header=True, header_style="bold magenta")
        status_table.add_column("指标", style="cyan", width=20)
        status_table.add_column("数值", style="white", width=15)
        status_table.add_column("状态", style="green", width=10)
        
        # CPU使用率
        cpu_usage = status_data.get("cpu_usage", 0)
        cpu_status = "🟢 正常" if cpu_usage < 80 else "🟡 高负载" if cpu_usage < 95 else "🔴 过载"
        status_table.add_row("CPU使用率", f"{cpu_usage:.1f}%", cpu_status)
        
        # 内存使用率
        memory_usage = status_data.get("memory_usage", 0)
        memory_status = "🟢 正常" if memory_usage < 80 else "🟡 偏高" if memory_usage < 95 else "🔴 不足"
        status_table.add_row("内存使用率", f"{memory_usage:.1f}%", memory_status)
        
        # GPU使用率
        gpu_usage = status_data.get("gpu_usage", 0)
        gpu_status = "🟢 正常" if gpu_usage < 80 else "🟡 繁忙" if gpu_usage < 95 else "🔴 满载"
        status_table.add_row("GPU使用率", f"{gpu_usage:.1f}%", gpu_status)
        
        # 会话信息
        active_sessions = status_data.get("active_sessions", 0)
        status_table.add_row("活跃会话", str(active_sessions), "🟢 正常")
        
        # 请求统计
        total_requests = status_data.get("total_requests", 0)
        status_table.add_row("总请求数", str(total_requests), "📈 统计")
        
        # 响应时间
        avg_response_time = status_data.get("avg_response_time", 0)
        time_status = "🟢 快速" if avg_response_time < 1000 else "🟡 一般" if avg_response_time < 3000 else "🔴 较慢"
        status_table.add_row("平均响应时间", f"{avg_response_time:.1f}ms", time_status)
        
        self.console.print(status_table)
        
        # 组件健康状态
        components = status_data.get("components_health", {})
        if components:
            self.console.print()
            components_table = Table(title="🔧 组件状态", show_header=True, header_style="bold blue")
            components_table.add_column("组件", style="cyan", width=20)
            components_table.add_column("状态", style="white", width=15)
            
            for component, healthy in components.items():
                status_icon = "🟢 健康" if healthy else "🔴 异常"
                components_table.add_row(component, status_icon)
            
            self.console.print(components_table)
    
    def show_plugins_list(self, plugins: List[Dict[str, Any]]):
        """显示插件列表"""
        plugins_table = Table(title=f"🔌 插件列表 ({len(plugins)}个)", show_header=True, header_style="bold magenta")
        plugins_table.add_column("名称", style="cyan", width=20)
        plugins_table.add_column("版本", style="white", width=10)
        plugins_table.add_column("状态", style="green", width=10)
        plugins_table.add_column("描述", style="white", width=40)
        
        for plugin in plugins:
            name = plugin.get("name", "Unknown")
            version = plugin.get("version", "0.0.0")
            enabled = plugin.get("enabled", False)
            description = plugin.get("description", "无描述")
            
            status = "🟢 启用" if enabled else "🔴 禁用"
            
            plugins_table.add_row(name, version, status, description)
        
        self.console.print(plugins_table)
        
        # 显示能力统计
        if plugins:
            self.console.print()
            capabilities = {}
            for plugin in plugins:
                for cap in plugin.get("capabilities", []):
                    capabilities[cap] = capabilities.get(cap, 0) + 1
            
            if capabilities:
                caps_text = Text("🎯 插件能力统计: ", style="bold white")
                for cap, count in capabilities.items():
                    caps_text.append(f"{cap}({count}) ", style="cyan")
                
                self.console.print(Panel(caps_text, border_style="dim"))
    
    def show_error(self, error_message: str, details: Optional[str] = None):
        """显示错误信息"""
        error_text = Text.assemble(
            ("❌ 错误", "bold red"),
            "\n",
            (error_message, "red")
        )
        
        if details:
            error_text.append("\n\n详细信息:\n", style="dim")
            error_text.append(details, style="white")
        
        error_panel = Panel(
            error_text,
            title="[bold red]错误[/bold red]",
            border_style="red",
            padding=(0, 1)
        )
        
        self.console.print(error_panel)
        self.console.print()
    
    def show_help(self, commands: Dict[str, str]):
        """显示帮助信息"""
        help_table = Table(title="📋 命令帮助", show_header=True, header_style="bold green")
        help_table.add_column("命令", style="cyan", width=20)
        help_table.add_column("说明", style="white", width=50)
        
        for command, description in commands.items():
            help_table.add_row(command, description)
        
        self.console.print(help_table)
        
        # 显示使用示例
        self.console.print()
        examples_text = Text.assemble(
            ("💡 使用示例:", "bold yellow"),
            "\n",
            ("  /chat 今天天气怎么样?", "green"),
            "\n",
            ("  /stream 写一首关于春天的诗", "green"),
            "\n",
            ("  /status", "green"),
            "\n",
            ("  /plugins", "green")
        )
        
        examples_panel = Panel(examples_text, title="示例", border_style="yellow")
        self.console.print(examples_panel)
    
    def show_result(self, result: Dict[str, Any]):
        """显示通用结果"""
        if "error" in result:
            self.show_error(result["error"], result.get("details"))
        elif "content" in result:
            self.show_ai_response(result["content"], result)
        else:
            # 其他类型的结果
            self.console.print(Panel(str(result), border_style="white"))
    
    def _format_model_info(self, metadata: Dict[str, Any]) -> str:
        """格式化模型信息"""
        model_used = metadata.get("model_used")
        reasoning = metadata.get("reasoning")
        
        if model_used and reasoning:
            return f"⚡{model_used} ({reasoning})"
        elif model_used:
            return f"⚡{model_used}"
        else:
            return ""
    
    def _show_performance_stats(self, metadata: Dict[str, Any]):
        """显示性能统计"""
        stats_parts = []
        
        # 响应时间
        response_time = metadata.get("response_time")
        if response_time:
            stats_parts.append(f"⏱️ 响应时间: {response_time:.1f}s")
        
        # 成本信息
        cost = metadata.get("cost")
        if cost is not None:
            if cost == 0:
                stats_parts.append("💰 成本: 免费")
            else:
                stats_parts.append(f"💰 成本: ${cost:.4f}")
        
        # 使用的插件
        plugins_used = metadata.get("plugins_used")
        if plugins_used:
            if isinstance(plugins_used, list):
                plugins_str = ", ".join(plugins_used)
            else:
                plugins_str = str(plugins_used)
            stats_parts.append(f"🔧 插件: {plugins_str}")
        
        if stats_parts:
            stats_text = " | ".join(stats_parts)
            stats_panel = Panel(
                Text(stats_text, style="dim"),
                border_style="dim",
                padding=(0, 1)
            )
            self.console.print(stats_panel)
    
    def _is_code_block(self, content: str) -> bool:
        """判断是否为代码块"""
        # 简单的代码检测逻辑
        code_indicators = ["def ", "class ", "import ", "from ", "```", "function", "const ", "let "]
        return any(indicator in content.lower() for indicator in code_indicators)
    
    def _is_markdown(self, content: str) -> bool:
        """判断是否为Markdown内容"""
        # 简单的Markdown检测逻辑
        markdown_indicators = ["# ", "## ", "### ", "**", "*", "`", "- ", "1. ", "[", "]("]
        return any(indicator in content for indicator in markdown_indicators)


class StreamingDisplay:
    """流式显示辅助类"""
    
    def __init__(self, live_display: Live, layout: Layout):
        self.live_display = live_display
        self.layout = layout
        self.content_buffer = ""
        self.token_count = 0
        
    def add_content(self, content: str):
        """添加流式内容"""
        self.content_buffer += content
        self.token_count += len(content.split())
        
        # 更新显示
        self.layout["content"].update(
            Panel(Text(self.content_buffer, style="white"), border_style="green")
        )
        
        # 更新状态
        status_text = Text.assemble(
            ("📊 进度: ", "white"),
            ("████████░░ 80%", "green"),  # 这里可以根据实际进度计算
            (" | 🔢 Token: ", "white"),
            (f"{self.token_count}/2048", "cyan"),
            (" | ⏱️ 已用时: 3.2s", "white")
        )
        
        self.layout["footer"].update(
            Panel(status_text, border_style="dim")
        )
    
    def finish(self, metadata: Optional[Dict[str, Any]] = None):
        """完成流式显示"""
        # 更新最终状态
        final_title = Text.assemble(
            ("🤖 AI助手", "bold green"),
            (f" ({datetime.now().strftime('%H:%M')})", "dim"),
            (" ✅ 完成", "green")
        )
        
        self.layout["header"].update(Panel(final_title, border_style="green"))
        
        # 停止实时显示
        self.live_display.stop()
        
        # 显示最终内容
        final_panel = Panel(
            Text(self.content_buffer, style="white"),
            title=final_title,
            border_style="green",
            padding=(0, 1)
        )
        
        # 清除实时显示并显示最终结果
        self.live_display.console.print(final_panel)
        
        # 显示性能统计
        if metadata:
            display_engine = DisplayEngine(self.live_display.console)
            display_engine._show_performance_stats(metadata)