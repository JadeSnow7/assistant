"""
高级流式显示组件 - 提供实时进度指示和丰富的可视化效果
"""
import asyncio
import time
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.live import Live
from rich.layout import Layout
from rich.table import Table
from rich.align import Align
from rich.markdown import Markdown
from rich.syntax import Syntax


class AdvancedStreamingDisplay:
    """高级流式显示组件"""
    
    def __init__(self, console: Console, title: str = "AI响应"):
        self.console = console
        self.title = title
        self.start_time = time.time()
        self.content_buffer = ""
        self.token_count = 0
        self.char_count = 0
        self.estimated_total_tokens = 500  # 预估总token数
        self.live_display: Optional[Live] = None
        self.layout: Optional[Layout] = None
        self.is_active = False
        
        # 性能统计
        self.chunks_received = 0
        self.avg_chunk_size = 0
        self.tokens_per_second = 0
        
        # 显示选项
        self.show_progress = True
        self.show_stats = True
        self.show_preview = True
        self.animate_typing = True
        
    def start(self, metadata: Optional[Dict[str, Any]] = None):
        """开始流式显示"""
        if self.is_active:
            return
            
        self.is_active = True
        
        # 创建布局
        self.layout = Layout()
        self.layout.split_column(
            Layout(name="header", size=4),
            Layout(name="content", ratio=3),
            Layout(name="footer", size=6)
        )
        
        # 初始化各部分
        self._update_header("🎭 正在思考中...")
        self._update_content("")
        self._update_footer()
        
        # 启动实时显示
        self.live_display = Live(
            self.layout, 
            console=self.console, 
            refresh_per_second=10,
            transient=False
        )
        self.live_display.start()
        
        return self
    
    def add_chunk(self, chunk: str, metadata: Optional[Dict[str, Any]] = None):
        """添加内容块"""
        if not self.is_active:
            return
            
        # 更新统计信息
        self.content_buffer += chunk
        self.char_count += len(chunk)
        self.token_count += self._estimate_tokens(chunk)
        self.chunks_received += 1
        
        # 计算平均块大小和速度
        self.avg_chunk_size = self.char_count / self.chunks_received
        elapsed_time = time.time() - self.start_time
        if elapsed_time > 0:
            self.tokens_per_second = self.token_count / elapsed_time
        
        # 更新显示
        self._update_header("✨ 正在生成中...")
        self._update_content(self.content_buffer)
        self._update_footer()
    
    def finish(self, metadata: Optional[Dict[str, Any]] = None):
        """完成流式显示"""
        if not self.is_active:
            return
            
        self.is_active = False
        
        # 最终更新
        self._update_header("✅ 生成完成")
        self._update_content(self.content_buffer)
        self._update_footer(final=True, metadata=metadata)
        
        # 停止实时显示
        if self.live_display:
            self.live_display.stop()
        
        # 显示最终结果面板
        self._show_final_result(metadata)
    
    def cancel(self, reason: str = "用户取消"):
        """取消流式显示"""
        if not self.is_active:
            return
            
        self.is_active = False
        
        # 更新为取消状态
        self._update_header(f"❌ {reason}")
        self._update_footer(final=True)
        
        # 停止实时显示
        if self.live_display:
            self.live_display.stop()
        
        # 显示取消消息
        cancel_panel = Panel(
            Text.assemble(
                ("❌ ", "red"),
                (reason, "yellow"),
                "\n",
                (f"已生成 {self.token_count} tokens", "dim")
            ),
            title="[red]已取消[/red]",
            border_style="red"
        )
        self.console.print(cancel_panel)
    
    def _update_header(self, status: str):
        """更新头部状态"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        header_text = Text.assemble(
            ("🤖 ", "blue"),
            (self.title, "bold cyan"),
            (f" ({timestamp})", "dim"),
            (" - ", "white"),
            (status, "yellow" if "思考" in status or "生成" in status else "green")
        )
        
        header_panel = Panel(
            Align.center(header_text),
            border_style="blue"
        )
        
        if self.layout:
            self.layout["header"].update(header_panel)
    
    def _update_content(self, content: str):
        """更新内容区域"""
        if not self.layout:
            return
            
        if not content:
            placeholder = Text("等待AI响应...", style="dim italic")
            content_panel = Panel(
                Align.center(placeholder),
                border_style="dim"
            )
        else:
            # 检测内容类型并应用相应格式
            if self._is_code_content(content):
                # 代码内容
                try:
                    content_display = Syntax(
                        content, 
                        "python",  # 可以根据内容自动检测
                        theme="monokai",
                        line_numbers=False,
                        word_wrap=True
                    )
                except Exception:
                    content_display = Text(content, style="white")
            elif self._is_markdown_content(content):
                # Markdown内容
                try:
                    content_display = Markdown(content)
                except Exception:
                    content_display = Text(content, style="white")
            else:
                # 普通文本
                content_display = Text(content, style="white")
            
            # 添加打字机效果的光标
            if self.animate_typing and self.is_active:
                cursor_text = Text("█", style="bold white blink")
                if isinstance(content_display, Text):
                    content_display.append(cursor_text)
            
            content_panel = Panel(
                content_display,
                border_style="green",
                padding=(0, 1)
            )
        
        self.layout["content"].update(content_panel)
    
    def _update_footer(self, final: bool = False, metadata: Optional[Dict[str, Any]] = None):
        """更新底部统计信息"""
        if not self.layout:
            return
            
        elapsed_time = time.time() - self.start_time
        
        # 创建统计表格
        stats_table = Table.grid(padding=1)
        stats_table.add_column(style="cyan", justify="left")
        stats_table.add_column(style="white", justify="left")
        stats_table.add_column(style="cyan", justify="left")
        stats_table.add_column(style="white", justify="left")
        
        # 进度信息
        if not final:
            progress_percent = min(100, (self.token_count / self.estimated_total_tokens) * 100)
            progress_bar = self._create_progress_bar(progress_percent)
            stats_table.add_row("📊 进度:", progress_bar, "⏱️ 用时:", f"{elapsed_time:.1f}s")
        else:
            stats_table.add_row("✅ 完成:", "100%", "⏱️ 用时:", f"{elapsed_time:.1f}s")
        
        # Token统计
        stats_table.add_row(
            "🔢 Tokens:", f"{self.token_count}",
            "⚡ 速度:", f"{self.tokens_per_second:.1f} tokens/s"
        )
        
        # 字符统计
        stats_table.add_row(
            "📝 字符:", f"{self.char_count}",
            "📦 块数:", f"{self.chunks_received}"
        )
        
        # 如果是最终状态，添加元数据信息
        if final and metadata:
            if metadata.get("model_used"):
                stats_table.add_row("🎯 模型:", metadata["model_used"], "", "")
            
            if metadata.get("cost") is not None:
                cost = metadata["cost"]
                cost_text = "免费" if cost == 0 else f"${cost:.4f}"
                stats_table.add_row("💰 成本:", cost_text, "", "")
            
            if metadata.get("plugins_used"):
                plugins = metadata["plugins_used"]
                if isinstance(plugins, list):
                    plugins_text = ", ".join(plugins)
                else:
                    plugins_text = str(plugins)
                stats_table.add_row("🔧 插件:", plugins_text, "", "")
        
        footer_panel = Panel(
            stats_table,
            title="[dim]实时统计[/dim]",
            border_style="dim"
        )
        
        self.layout["footer"].update(footer_panel)
    
    def _create_progress_bar(self, percent: float) -> str:
        """创建进度条"""
        bar_length = 20
        filled_length = int(bar_length * percent / 100)
        bar = "█" * filled_length + "░" * (bar_length - filled_length)
        return f"{bar} {percent:.1f}%"
    
    def _estimate_tokens(self, text: str) -> int:
        """估算token数量"""
        # 简单的token估算，实际应该使用tokenizer
        return len(text.split())
    
    def _is_code_content(self, content: str) -> bool:
        """检测是否为代码内容"""
        code_indicators = [
            "def ", "class ", "import ", "from ", "function", 
            "const ", "let ", "var ", "if (", "for (", "while (",
            "{", "}", "```", "#!/"
        ]
        return any(indicator in content for indicator in code_indicators)
    
    def _is_markdown_content(self, content: str) -> bool:
        """检测是否为Markdown内容"""
        markdown_indicators = ["# ", "## ", "### ", "**", "*", "`", "- ", "1. "]
        return any(indicator in content for indicator in markdown_indicators)
    
    def _show_final_result(self, metadata: Optional[Dict[str, Any]] = None):
        """显示最终结果"""
        # 创建最终结果面板
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # 标题
        title_text = Text.assemble(
            ("🤖 ", "blue"),
            (self.title, "bold green"),
            (f" ({timestamp})", "dim"),
            (" ✅", "green")
        )
        
        # 内容
        if self._is_code_content(self.content_buffer):
            try:
                content_display = Syntax(
                    self.content_buffer,
                    "python",
                    theme="monokai",
                    line_numbers=True
                )
            except Exception:
                content_display = Text(self.content_buffer, style="white")
        elif self._is_markdown_content(self.content_buffer):
            try:
                content_display = Markdown(self.content_buffer)
            except Exception:
                content_display = Text(self.content_buffer, style="white")
        else:
            content_display = Text(self.content_buffer, style="white")
        
        final_panel = Panel(
            content_display,
            title=title_text,
            border_style="green",
            padding=(0, 1)
        )
        
        self.console.print(final_panel)
        
        # 显示性能统计
        if self.show_stats:
            self._show_performance_summary(metadata)
        
        self.console.print()  # 添加空行
    
    def _show_performance_summary(self, metadata: Optional[Dict[str, Any]] = None):
        """显示性能摘要"""
        elapsed_time = time.time() - self.start_time
        
        summary_parts = []
        
        # 响应时间
        summary_parts.append(f"⏱️ 响应时间: {elapsed_time:.1f}s")
        
        # Token统计
        summary_parts.append(f"🔢 Tokens: {self.token_count}")
        
        # 速度
        summary_parts.append(f"⚡ 速度: {self.tokens_per_second:.1f} tokens/s")
        
        # 元数据信息
        if metadata:
            if metadata.get("cost") is not None:
                cost = metadata["cost"]
                cost_text = "💰 免费" if cost == 0 else f"💰 ${cost:.4f}"
                summary_parts.append(cost_text)
            
            if metadata.get("plugins_used"):
                plugins = metadata["plugins_used"]
                if isinstance(plugins, list):
                    plugins_text = ", ".join(plugins)
                else:
                    plugins_text = str(plugins)
                summary_parts.append(f"🔧 {plugins_text}")
        
        if summary_parts:
            summary_text = " | ".join(summary_parts)
            summary_panel = Panel(
                Text(summary_text, style="dim"),
                border_style="dim",
                padding=(0, 1)
            )
            self.console.print(summary_panel)


class ProgressTracker:
    """进度跟踪器"""
    
    def __init__(self, console: Console, description: str = "处理中"):
        self.console = console
        self.description = description
        self.start_time = time.time()
        self.progress: Optional[Progress] = None
        self.task_id = None
        
    def start(self, total: Optional[float] = None):
        """开始进度跟踪"""
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=self.console
        )
        
        self.progress.start()
        self.task_id = self.progress.add_task(
            self.description, 
            total=total or 100
        )
        
        return self
    
    def update(self, advance: float = 1, description: Optional[str] = None):
        """更新进度"""
        if self.progress and self.task_id is not None:
            kwargs = {"advance": advance}
            if description:
                kwargs["description"] = description
            self.progress.update(self.task_id, **kwargs)
    
    def finish(self, description: Optional[str] = None):
        """完成进度跟踪"""
        if self.progress and self.task_id is not None:
            if description:
                self.progress.update(self.task_id, description=description)
            self.progress.stop()
            
        elapsed_time = time.time() - self.start_time
        completion_text = Text.assemble(
            ("✅ ", "green"),
            (description or "完成", "white"),
            (f" (用时 {elapsed_time:.1f}s)", "dim")
        )
        self.console.print(completion_text)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.progress:
            self.progress.stop()