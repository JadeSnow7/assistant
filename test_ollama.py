#!/usr/bin/env python3
"""
Ollama集成测试脚本
"""
import asyncio
import logging
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'python'))

from core.ollama_client import OllamaClient
from core.grpc_client import GRPCClient
from agent.orchestrator import AgentOrchestrator
from models.schemas import ChatRequest

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_ollama_client():
    """测试Ollama客户端"""
    logger.info("🧪 测试Ollama客户端...")
    
    client = OllamaClient()
    
    try:
        await client.initialize()
        logger.info("✅ Ollama客户端初始化成功")
        
        # 获取可用模型
        models = await client.get_available_models()
        logger.info(f"✅ 可用模型: {models}")
        
        # 测试聊天
        messages = [{"role": "user", "content": "你好，请简单介绍一下你自己"}]
        response = await client.chat_completion(messages)
        
        if "error" not in response:
            logger.info(f"✅ 聊天测试成功:")
            logger.info(f"  📝 回复: {response['content'][:100]}...")
            logger.info(f"  🧠 模型: {response.get('model')}")
            logger.info(f"  ⏱️ 延迟: {response.get('latency_ms', 0):.1f}ms")
        else:
            logger.error(f"❌ 聊天测试失败: {response['error']}")
        
        await client.cleanup()
        return True
        
    except Exception as e:
        logger.error(f"❌ Ollama客户端测试失败: {e}")
        return False


async def test_grpc_with_ollama():
    """测试集成Ollama的gRPC客户端"""
    logger.info("🔧 测试gRPC客户端（集成Ollama）...")
    
    grpc_client = GRPCClient()
    
    try:
        await grpc_client.connect()
        logger.info("✅ gRPC客户端连接成功")
        
        # 测试推理
        response = await grpc_client.inference(
            prompt="请用一句话介绍人工智能",
            max_tokens=100
        )
        
        logger.info(f"✅ 推理测试成功:")
        logger.info(f"  📝 回复: {response['text'][:100]}...")
        logger.info(f"  🧠 模型: {response.get('used_model')}")
        logger.info(f"  ⏱️ 延迟: {response.get('latency_ms', 0):.1f}ms")
        
        # 获取模型列表
        models = await grpc_client.get_available_models()
        logger.info(f"✅ 可用模型: {models}")
        
        await grpc_client.disconnect()
        return True
        
    except Exception as e:
        logger.error(f"❌ gRPC客户端测试失败: {e}")
        return False


async def test_agent_with_ollama():
    """测试集成Ollama的Agent调度器"""
    logger.info("🤖 测试Agent调度器（集成Ollama）...")
    
    grpc_client = GRPCClient()
    orchestrator = AgentOrchestrator(grpc_client)
    
    try:
        await orchestrator.initialize()
        logger.info("✅ Agent调度器初始化成功")
        
        # 测试简单对话
        test_cases = [
            "你好，请介绍一下你自己",
            "今天天气怎么样？",  # 应该被识别为需要插件
            "请详细分析一下人工智能的发展趋势",  # 复杂任务
        ]
        
        for i, message in enumerate(test_cases, 1):
            logger.info(f"\n--- 测试用例 {i}: {message} ---")
            
            request = ChatRequest(
                message=message,
                session_id=f"test_session_{i}"
            )
            
            response = await orchestrator.process_chat(request)
            
            logger.info(f"✅ 对话{i}成功:")
            logger.info(f"  📝 回复: {response.content[:100]}...")
            logger.info(f"  🧠 使用模型: {response.model_used}")
            logger.info(f"  💭 决策原因: {response.reasoning}")
            logger.info(f"  ⏱️ 响应时间: {response.latency_ms or 0:.1f}ms")
        
        # 获取统计信息
        stats = orchestrator.get_stats()
        logger.info(f"\n✅ 性能统计: {stats}")
        
        await orchestrator.cleanup()
        return True
        
    except Exception as e:
        logger.error(f"❌ Agent调度器测试失败: {e}")
        return False


async def main():
    """主测试函数"""
    logger.info("🚀 开始Ollama集成测试")
    logger.info("=" * 60)
    
    test_functions = [
        ("Ollama客户端", test_ollama_client),
        ("gRPC客户端(集成Ollama)", test_grpc_with_ollama),
        ("Agent调度器(集成Ollama)", test_agent_with_ollama),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in test_functions:
        try:
            logger.info(f"\n🔍 开始测试: {test_name}")
            success = await test_func()
            if success:
                passed += 1
                logger.info(f"✅ {test_name} 测试通过")
            else:
                failed += 1
                logger.error(f"❌ {test_name} 测试失败")
        except Exception as e:
            failed += 1
            logger.error(f"❌ {test_name} 测试异常: {e}")
        
        logger.info("=" * 60)
    
    logger.info(f"\n🏁 测试完成")
    logger.info(f"✅ 通过: {passed}")
    logger.info(f"❌ 失败: {failed}")
    logger.info(f"📊 成功率: {passed/(passed+failed)*100:.1f}%")
    
    if failed == 0:
        logger.info("🎉 所有Ollama集成测试通过！")
        return True
    else:
        logger.warning("⚠️  部分测试失败，请检查Ollama服务状态")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("测试被用户中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"测试运行异常: {e}")
        sys.exit(1)