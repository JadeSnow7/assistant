#!/usr/bin/env python3
"""
AI Assistant CLI 测试脚本
"""
import asyncio
import aiohttp
import json

class SimpleAIClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session_id = "test-session-" + str(hash("test"))[:8]
    
    async def chat(self, message):
        """发送聊天消息"""
        data = {
            "message": message,
            "session_id": self.session_id
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.base_url}/api/v1/chat", json=data, timeout=30) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result
                    else:
                        error = await response.text()
                        return {"error": f"HTTP {response.status}: {error}"}
        except Exception as e:
            return {"error": f"连接错误: {str(e)}"}

async def main():
    print("🤖 AI Assistant CLI 测试工具")
    print("=" * 50)
    
    client = SimpleAIClient()
    
    # 测试用例
    test_messages = [
        "你好，请介绍一下你自己",
        "什么是机器学习？", 
        "用Python写一个简单的计算器",
        "今天天气怎么样？"
    ]
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n📝 测试 {i}: {message}")
        print("-" * 40)
        
        result = await client.chat(message)
        
        if "error" in result:
            print(f"❌ 错误: {result['error']}")
        else:
            # 清理AI回复内容，去掉思考过程
            content = result.get("content", "")
            if "<think>" in content and "</think>" in content:
                # 提取</think>后的内容
                content = content.split("</think>")[-1].strip()
            
            print(f"🤖 AI回复: {content}")
            print(f"📊 使用模型: {result.get('model_used', 'N/A')}")
            print(f"💭 推理过程: {result.get('reasoning', 'N/A')}")
            print(f"⏰ 响应时间: {result.get('latency_ms', 'N/A')} ms")
        
        # 等待一下再进行下个测试
        await asyncio.sleep(1)
    
    print("\n✅ 测试完成！")

if __name__ == "__main__":
    asyncio.run(main())