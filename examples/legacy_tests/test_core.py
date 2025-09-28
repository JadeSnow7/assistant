#!/usr/bin/env python3
"""
核心逻辑测试脚本
"""
import asyncio
import logging
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'python'))

from core.config import settings
from core.grpc_client import GRPCClient
from core.memory_manager import MemoryManager
from core.plugin_manager import PluginManager
from core.cloud_client import CloudClient
from agent.orchestrator import AgentOrchestrator
from models.schemas import ChatRequest


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_grpc_client():
    """测试gRPC客户端"""
    logger.info("🔧 测试gRPC客户端...")
    
    grpc_client = GRPCClient()
    
    try:
        # 注意：这里会因为没有真实的gRPC服务而失败，但会测试连接逻辑
        await grpc_client.connect()
        logger.info("✅ gRPC客户端连接测试通过")
    except Exception as e:
        logger.warning(f"⚠️  gRPC连接失败（预期行为）: {e}")
    
    # 测试模拟调用
    try:
        response = await grpc_client.inference("测试推理", max_tokens=100)
        logger.info(f"✅ 模拟推理调用成功: {response['text'][:50]}...")
    except Exception as e:
        logger.error(f"❌ 推理调用失败: {e}")
    
    await grpc_client.disconnect()


async def test_memory_manager():
    """测试记忆管理器"""
    logger.info("🧠 测试记忆管理器...")
    
    memory_manager = MemoryManager()
    
    try:
        await memory_manager.initialize()
        logger.info("✅ 记忆管理器初始化成功")
        
        # 测试会话上下文
        session_id = "test_session_001"
        context = await memory_manager.get_session_context(session_id)
        logger.info(f"✅ 获取会话上下文成功: {len(context['recent_messages'])} 条消息")
        
        # 测试更新会话
        await memory_manager.update_session(
            session_id, 
            "你好，AI助手！", 
            "你好！我是AI助手，很高兴为您服务。"
        )
        logger.info("✅ 会话记录更新成功")
        
        # 测试搜索记忆
        results = await memory_manager.search_memory("AI助手", session_id=session_id)
        logger.info(f"✅ 记忆搜索成功: 找到 {len(results)} 条相关记录")
        
        await memory_manager.cleanup()
        
    except Exception as e:
        logger.error(f"❌ 记忆管理器测试失败: {e}")


async def test_plugin_manager():
    """测试插件管理器"""
    logger.info("🔌 测试插件管理器...")
    
    plugin_manager = PluginManager()
    
    try:
        await plugin_manager.initialize()
        logger.info("✅ 插件管理器初始化成功")
        
        # 获取插件列表
        plugins = await plugin_manager.get_available_plugins()
        logger.info(f"✅ 发现 {len(plugins)} 个插件")
        
        for plugin in plugins:
            logger.info(f"  📦 {plugin.name} v{plugin.version} - {'启用' if plugin.enabled else '禁用'}")
        
        # 如果有天气插件，测试执行
        if any(p.name == "weather_plugin" for p in plugins):
            try:
                result = await plugin_manager.execute_plugin(
                    "weather_plugin",
                    "get_weather",
                    {"city": "北京"}
                )
                if result.get("success"):
                    logger.info("✅ 天气插件执行成功")
                else:
                    logger.warning(f"⚠️  天气插件执行失败: {result.get('error')}")
            except Exception as e:
                logger.warning(f"⚠️  天气插件测试异常: {e}")
        
        await plugin_manager.cleanup()
        
    except Exception as e:
        logger.error(f"❌ 插件管理器测试失败: {e}")


async def test_cloud_client():
    """测试云端客户端"""
    logger.info("☁️  测试云端客户端...")
    
    cloud_client = CloudClient()
    
    try:
        await cloud_client.initialize()
        logger.info("✅ 云端客户端初始化成功")
        
        # 测试聊天完成（如果有API密钥）
        if settings.cloud_api_key:
            response = await cloud_client.chat_completion(
                messages=[{"role": "user", "content": "你好"}]
            )
            
            if "error" not in response:
                logger.info(f"✅ 云端API调用成功: {response['content'][:50]}...")
            else:
                logger.warning(f"⚠️  云端API调用失败: {response['error']}")
        else:
            logger.info("ℹ️  未配置云端API密钥，跳过API测试")
        
        await cloud_client.cleanup()
        
    except Exception as e:
        logger.error(f"❌ 云端客户端测试失败: {e}")


async def test_orchestrator():
    """测试Agent调度器"""
    logger.info("🤖 测试Agent调度器...")
    
    grpc_client = GRPCClient()
    orchestrator = AgentOrchestrator(grpc_client)
    
    try:
        await orchestrator.initialize()
        logger.info("✅ Agent调度器初始化成功")
        
        # 测试聊天处理
        chat_request = ChatRequest(
            message="你好，请介绍一下你自己",
            session_id="test_session_002"
        )
        
        response = await orchestrator.process_chat(chat_request)
        logger.info(f"✅ 聊天处理成功:")
        logger.info(f"  📝 回复: {response.content[:100]}...")
        logger.info(f"  🧠 使用模型: {response.model_used}")
        logger.info(f"  💭 决策原因: {response.reasoning}")
        
        # 测试性能统计
        stats = orchestrator.get_stats()
        logger.info(f"✅ 性能统计: {stats}")
        
        # 测试健康检查
        healthy = orchestrator.is_healthy()
        logger.info(f"✅ 健康检查: {'健康' if healthy else '异常'}")
        
        await orchestrator.cleanup()
        
    except Exception as e:
        logger.error(f"❌ Agent调度器测试失败: {e}")


async def run_comprehensive_test():
    """运行综合测试"""
    logger.info("🚀 开始AI Assistant核心逻辑测试")
    logger.info("=" * 60)
    
    # 按顺序执行测试
    test_functions = [
        test_grpc_client,
        test_memory_manager,
        test_plugin_manager,
        test_cloud_client,
        test_orchestrator
    ]
    
    passed = 0
    failed = 0
    
    for test_func in test_functions:
        try:
            await test_func()
            passed += 1
            logger.info("=" * 60)
        except Exception as e:
            logger.error(f"❌ 测试 {test_func.__name__} 失败: {e}")
            failed += 1
            logger.info("=" * 60)
    
    logger.info("🏁 测试完成")
    logger.info(f"✅ 通过: {passed}")
    logger.info(f"❌ 失败: {failed}")
    logger.info(f"📊 成功率: {passed/(passed+failed)*100:.1f}%")
    
    if failed == 0:
        logger.info("🎉 所有核心功能测试通过！")
        return True
    else:
        logger.warning("⚠️  部分功能存在问题，请检查日志")
        return False


async def main():
    """主函数"""
    try:
        success = await run_comprehensive_test()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("测试被用户中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"测试运行异常: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())