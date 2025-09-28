#!/usr/bin/env python3
"""
云端模型集成测试脚本
"""
import asyncio
import aiohttp
import json

async def test_cloud_model():
    """测试云端模型功能"""
    print("🚀 测试云端模型集成")
    print("=" * 50)
    
    # 测试用例 - 复杂任务，应该触发云端模型
    complex_queries = [
        "请帮我写一个完整的Python机器学习项目，包含数据预处理、特征工程、模型训练和评估的详细代码实现",
        "请详细分析深度学习和传统机器学习的区别，并提供具体的应用场景和代码示例",
        "设计一个分布式系统架构，用于处理大并发量的电商平台，包括微服务设计、数据库选择和缓存策略"
    ]
    
    # 简单任务 - 应该使用本地模型
    simple_queries = [
        "你好，请介绍一下你自己",
        "今天天气怎么样？",
        "谢谢你的帮助"
    ]
    
    session_id = "cloud-test-001"
    
    print("🔥 测试复杂任务（预期使用云端模型）：")
    print("-" * 40)
    
    for i, query in enumerate(complex_queries, 1):
        print(f"📝 复杂测试 {i}: {query[:50]}...")
        
        result = await send_chat_request(query, session_id)
        
        if result:
            model_used = result.get("model_used", "unknown")
            reasoning = result.get("reasoning", "无说明")
            content_length = len(result.get("content", ""))
            
            print(f"🤖 使用模型: {model_used}")
            print(f"💭 路由原因: {reasoning}")
            print(f"📊 响应长度: {content_length} 字符")
            print(f"⏱️  响应时间: {result.get('latency_ms', 0):.1f} ms")
            
            if "cloud" in model_used.lower() or "gemini" in reasoning.lower():
                print("✅ 成功使用云端模型")
            elif "local" in model_used.lower():
                print("⚠️  使用了本地模型（可能是降级）")
            else:
                print("❓ 模型类型不明确")
        else:
            print("❌ 请求失败")
        
        print()
        await asyncio.sleep(1)
    
    print("💡 测试简单任务（预期使用本地模型）：")
    print("-" * 40)
    
    for i, query in enumerate(simple_queries, 1):
        print(f"📝 简单测试 {i}: {query}")
        
        result = await send_chat_request(query, session_id)
        
        if result:
            model_used = result.get("model_used", "unknown")
            reasoning = result.get("reasoning", "无说明")
            
            print(f"🤖 使用模型: {model_used}")
            print(f"💭 路由原因: {reasoning}")
            
            if "local" in model_used.lower():
                print("✅ 成功使用本地模型")
            elif "cloud" in model_used.lower():
                print("⚠️  使用了云端模型（可能过度使用）")
            else:
                print("❓ 模型类型不明确")
        else:
            print("❌ 请求失败")
        
        print()
        await asyncio.sleep(1)

async def send_chat_request(message, session_id):
    """发送聊天请求"""
    data = {
        "message": message,
        "session_id": session_id
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://localhost:8000/api/v1/chat", 
                json=data,
                timeout=60  # 云端模型可能需要更长时间
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    print(f"HTTP错误: {response.status}")
                    return None
    except Exception as e:
        print(f"请求异常: {e}")
        return None

if __name__ == "__main__":
    asyncio.run(test_cloud_model())