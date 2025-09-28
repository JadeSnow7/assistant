#!/usr/bin/env python3
import asyncio
import aiohttp
import json

async def test_chat():
    data = {'message': '你好，请介绍一下你自己', 'session_id': 'cli-test-001'}
    
    async with aiohttp.ClientSession() as session:
        async with session.post('http://localhost:8000/api/v1/chat', json=data) as response:
            if response.status == 200:
                result = await response.json()
                print('🤖 AI回复:', result.get('content', ''))
                print('📊 使用模型:', result.get('model_used', ''))
                print('💭 推理过程:', result.get('reasoning', ''))
                print('⏰ 响应时间:', result.get('latency_ms', ''), 'ms')
                print('🔢 Token数:', result.get('token_count', ''))
            else:
                print('❌ 错误:', response.status, await response.text())

if __name__ == "__main__":
    asyncio.run(test_chat())