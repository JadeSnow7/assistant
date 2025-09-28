#!/usr/bin/env python3
"""
简化的CLI客户端启动脚本
"""
import asyncio
import aiohttp
import json
from datetime import datetime

class SimpleAIClient:
    """简化的AI客户端"""
    
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session_id = f"cli-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    async def chat(self, message: str):
        """发送聊天消息"""
        data = {
            "message": message,
            "session_id": self.session_id
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.base_url}/api/v1/chat", json=data, timeout=30) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error = await response.text()
                        return {"error": f"HTTP {response.status}: {error}"}
        except Exception as e:
            return {"error": f"连接错误: {str(e)}"}
    
    async def health_check(self):
        """健康检查"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/health", timeout=5) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return {"status": "unhealthy", "error": f"HTTP {response.status}"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}


async def main():
    """主函数"""
    client = SimpleAIClient()
    
    print("🤖 AI Assistant CLI - 简化版")
    print("="*50)
    
    # 健康检查
    health = await client.health_check()
    if health.get("status") == "healthy":
        print("✅ 服务连接正常")
    else:
        print(f"⚠️  服务状态: {health.get('error', '未知错误')}")
        print("继续尝试连接...")
    
    print(f"📱 会话ID: {client.session_id}")
    print("💡 输入消息开始对话，输入 'quit' 或 'exit' 退出")
    print("="*50)
    
    while True:
        try:
            # 获取用户输入
            user_input = input("\n👤 你: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit', '退出']:
                print("👋 再见!")
                break
            
            if user_input.lower() in ['help', '帮助']:
                print("""
🔧 可用命令:
  - 任何文本: 与AI对话
  - help/帮助: 显示此帮助
  - quit/exit/退出: 退出程序
                """)
                continue
            
            # 发送消息并获取响应
            print("🤖 AI: ", end="", flush=True)
            result = await client.chat(user_input)
            
            if "error" in result:
                print(f"❌ 错误: {result['error']}")
            else:
                content = result.get("content", "抱歉，我没有理解您的问题")
                print(content)
                
                # 显示额外信息
                model_used = result.get("model_used", "unknown")
                reasoning = result.get("reasoning", "")
                latency = result.get("latency_ms", 0)
                
                print(f"\n💭 [模型: {model_used}] [推理: {reasoning}] [耗时: {latency:.1f}ms]")
        
        except KeyboardInterrupt:
            print("\n\n👋 检测到 Ctrl+C，退出程序")
            break
        except Exception as e:
            print(f"\n❌ 程序错误: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())