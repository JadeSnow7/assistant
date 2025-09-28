#!/usr/bin/env python3
"""
AI Assistant CLI客户端
"""
import asyncio
import aiohttp
import json
import sys
import argparse
from typing import Dict, Any, Optional
import websockets
from datetime import datetime


class AIAssistantClient:
    """AI Assistant客户端"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.api_url = f"{self.base_url}/api/v1"
        self.ws_url = self.base_url.replace("http", "ws") + "/ws"
        self.session_id: Optional[str] = None
    
    async def chat(self, message: str, **kwargs) -> Dict[str, Any]:
        """发送聊天消息"""
        data = {
            "message": message,
            "session_id": self.session_id,
            **kwargs
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.api_url}/chat", json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    if not self.session_id:
                        self.session_id = result.get("session_id")
                    return result
                else:
                    error = await response.text()
                    return {"error": f"请求失败: {error}"}
    
    async def chat_stream(self, message: str, **kwargs):
        """流式聊天"""
        data = {
            "message": message,
            "session_id": self.session_id,
            **kwargs
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.api_url}/chat/stream", json=data) as response:
                if response.status == 200:
                    async for line in response.content:
                        line = line.decode('utf-8').strip()
                        if line.startswith('data: '):
                            data_str = line[6:]  # 去掉 'data: '
                            try:
                                data = json.loads(data_str)
                                yield data
                            except json.JSONDecodeError:
                                continue
                else:
                    error = await response.text()
                    yield {"error": f"请求失败: {error}"}
    
    async def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.api_url}/system/status") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error = await response.text()
                    return {"error": f"请求失败: {error}"}
    
    async def list_plugins(self) -> Dict[str, Any]:
        """获取插件列表"""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.api_url}/plugins") as response:
                if response.status == 200:
                    return {"plugins": await response.json()}
                else:
                    error = await response.text()
                    return {"error": f"请求失败: {error}"}
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{self.base_url}/health", timeout=5) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return {"status": "unhealthy", "error": f"HTTP {response.status}"}
            except Exception as e:
                return {"status": "unhealthy", "error": str(e)}


class CLIInterface:
    """命令行界面"""
    
    def __init__(self):
        self.client = AIAssistantClient()
        self.commands = {
            "chat": self.chat_command,
            "stream": self.stream_command,
            "status": self.status_command,
            "plugins": self.plugins_command,
            "health": self.health_command,
            "help": self.help_command,
            "exit": self.exit_command,
            "quit": self.exit_command
        }
    
    async def chat_command(self, args: list):
        """聊天命令"""
        if not args:
            print("请输入消息内容")
            return
        
        message = " ".join(args)
        print(f"用户: {message}")
        print("AI: ", end="", flush=True)
        
        result = await self.client.chat(message)
        if "error" in result:
            print(f"错误: {result['error']}")
        else:
            print(result.get("content", "无响应"))
            if result.get("reasoning"):
                print(f"  (使用: {result.get('model_used')} - {result.get('reasoning')})")
    
    async def stream_command(self, args: list):
        """流式聊天命令"""
        if not args:
            print("请输入消息内容")
            return
        
        message = " ".join(args)
        print(f"用户: {message}")
        print("AI: ", end="", flush=True)
        
        full_response = ""
        async for chunk in self.client.chat_stream(message):
            if "error" in chunk:
                print(f"\n错误: {chunk['error']}")
                break
            
            content = chunk.get("content", "")
            print(content, end="", flush=True)
            full_response += content
        
        print()  # 换行
    
    async def status_command(self, args: list):
        """系统状态命令"""
        result = await self.client.get_system_status()
        if "error" in result:
            print(f"错误: {result['error']}")
        else:
            print("📊 系统状态:")
            print(f"  CPU使用率: {result.get('cpu_usage', 0):.1f}%")
            print(f"  内存使用率: {result.get('memory_usage', 0):.1f}%")
            print(f"  GPU使用率: {result.get('gpu_usage', 0):.1f}%")
            print(f"  活跃会话: {result.get('active_sessions', 0)}")
            print(f"  总请求数: {result.get('total_requests', 0)}")
            print(f"  平均响应时间: {result.get('avg_response_time', 0):.1f}ms")
            
            components = result.get('components_health', {})
            print("  组件状态:")
            for component, healthy in components.items():
                status = "🟢 健康" if healthy else "🔴 异常"
                print(f"    {component}: {status}")
    
    async def plugins_command(self, args: list):
        """插件列表命令"""
        result = await self.client.list_plugins()
        if "error" in result:
            print(f"错误: {result['error']}")
        else:
            plugins = result.get("plugins", [])
            print(f"🔌 插件列表 ({len(plugins)}个):")
            for plugin in plugins:
                status = "🟢 启用" if plugin.get("enabled") else "🔴 禁用"
                print(f"  {plugin.get('name')} v{plugin.get('version')} - {status}")
                print(f"    {plugin.get('description')}")
                print(f"    能力: {', '.join(plugin.get('capabilities', []))}")
                print()
    
    async def health_command(self, args: list):
        """健康检查命令"""
        result = await self.client.health_check()
        status = result.get("status", "unknown")
        
        if status == "healthy":
            print("🟢 服务健康")
        else:
            print(f"🔴 服务异常: {result.get('error', '未知错误')}")
        
        # 显示详细信息
        if "components" in result:
            print("组件状态:")
            for component, healthy in result["components"].items():
                status_icon = "🟢" if healthy else "🔴"
                print(f"  {status_icon} {component}")
    
    def help_command(self, args: list):
        """帮助命令"""
        print("AI Assistant CLI 命令:")
        print("  chat <消息>        - 发送聊天消息")
        print("  stream <消息>      - 流式聊天")
        print("  status            - 查看系统状态")
        print("  plugins           - 查看插件列表")
        print("  health            - 健康检查")
        print("  help              - 显示帮助")
        print("  exit/quit         - 退出")
        print()
        print("示例:")
        print("  chat 今天天气怎么样?")
        print("  stream 写一首关于春天的诗")
        print("  status")
    
    def exit_command(self, args: list):
        """退出命令"""
        print("再见! 👋")
        sys.exit(0)
    
    async def run_interactive(self):
        """运行交互式界面"""
        print("🤖 AI Assistant CLI v1.0.0")
        print("输入 'help' 查看帮助，输入 'exit' 退出")
        print("=" * 50)
        
        # 健康检查
        health = await self.client.health_check()
        if health.get("status") != "healthy":
            print(f"⚠️  服务连接异常: {health.get('error')}")
            print("请确保服务正在运行")
        
        while True:
            try:
                # 显示提示符
                session_info = f"[{self.client.session_id[:8]}]" if self.client.session_id else "[new]"
                user_input = input(f"\n{session_info} > ").strip()
                
                if not user_input:
                    continue
                
                # 解析命令
                parts = user_input.split()
                command = parts[0].lower()
                args = parts[1:]
                
                # 执行命令
                if command in self.commands:
                    await self.commands[command](args)
                else:
                    # 默认为聊天命令
                    await self.chat_command([user_input])
            
            except KeyboardInterrupt:
                print("\n\n使用 'exit' 退出")
            except EOFError:
                self.exit_command([])
            except Exception as e:
                print(f"错误: {e}")
    
    async def run_single_command(self, command: str, args: list):
        """运行单个命令"""
        if command in self.commands:
            await self.commands[command](args)
        else:
            print(f"未知命令: {command}")
            print("使用 'help' 查看可用命令")


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="AI Assistant CLI客户端")
    parser.add_argument("--url", default="http://localhost:8000", 
                       help="AI Assistant服务地址")
    parser.add_argument("command", nargs="?", help="要执行的命令")
    parser.add_argument("args", nargs="*", help="命令参数")
    
    args = parser.parse_args()
    
    # 创建CLI界面
    cli = CLIInterface()
    cli.client = AIAssistantClient(args.url)
    
    if args.command:
        # 单命令模式
        await cli.run_single_command(args.command, args.args)
    else:
        # 交互模式
        await cli.run_interactive()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n再见! 👋")