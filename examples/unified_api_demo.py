"""
统一API系统演示脚本
"""
import asyncio
import json
import os
from typing import Dict, Any

# 添加项目根目录到Python路径
import sys
sys.path.append('/home/snow/workspace/nex/python')

from core.adapters import UnifiedChatRequest, ProviderType
from core.unified_api_gateway import UnifiedAPIGateway
from core.config_manager import initialize_config_manager, get_config


async def demo_basic_chat():
    """演示基本聊天功能"""
    print("🔹 演示基本聊天功能")
    
    # 创建聊天请求
    request = UnifiedChatRequest(
        model="auto",  # 自动选择模型
        messages=[
            {"role": "user", "content": "你好，请介绍一下自己"}
        ],
        max_tokens=200,
        temperature=0.7
    )
    
    # 创建网关实例
    gateway = UnifiedAPIGateway()
    
    try:
        # 初始化网关
        print("  正在初始化API网关...")
        success = await gateway.initialize()
        
        if not success:
            print("  ⚠️ 网关初始化失败，但继续演示")
        
        # 处理聊天请求
        print("  正在处理聊天请求...")
        response = await gateway.handle_chat_completion(request)
        
        # 输出结果
        print(f"  ✅ 响应成功")
        print(f"  📝 使用模型: {response.model} ({response.provider})")
        print(f"  💬 回复内容: {response.choices[0]['message']['content'][:100]}...")
        
        if response.usage:
            print(f"  📊 Token使用: {response.usage['total_tokens']} tokens")
        
        if response.performance:
            print(f"  ⚡ 响应时间: {response.performance['latency_ms']:.0f}ms")
    
    except Exception as e:
        print(f"  ❌ 演示失败: {e}")
    
    finally:
        await gateway.cleanup()


async def demo_model_selection():
    """演示模型选择功能"""
    print("\n🔹 演示模型选择功能")
    
    gateway = UnifiedAPIGateway()
    
    try:
        await gateway.initialize()
        
        # 测试不同的模型选择
        test_cases = [
            {
                "provider": "auto",
                "model": "auto",
                "message": "简单问候：你好",
                "description": "自动选择（简单任务）"
            },
            {
                "provider": "auto", 
                "model": "auto",
                "message": "复杂任务：请详细分析人工智能的发展趋势，包括技术挑战和机遇",
                "description": "自动选择（复杂任务）"
            }
        ]
        
        for i, case in enumerate(test_cases):
            print(f"\n  测试 {i+1}: {case['description']}")
            print(f"  📝 输入: {case['message'][:50]}...")
            
            request = UnifiedChatRequest(
                model=case["model"],
                messages=[{"role": "user", "content": case["message"]}],
                provider=case["provider"],
                max_tokens=100
            )
            
            response = await gateway.handle_chat_completion(request)
            print(f"  🎯 选择模型: {response.model} ({response.provider})")
            
            # 如果有性能数据，显示
            if response.performance:
                latency = response.performance.get('latency_ms', 0)
                print(f"  ⚡ 响应时间: {latency:.0f}ms")
    
    except Exception as e:
        print(f"  ❌ 演示失败: {e}")
    
    finally:
        await gateway.cleanup()


async def demo_available_models():
    """演示可用模型查询"""
    print("\n🔹 演示可用模型查询")
    
    gateway = UnifiedAPIGateway()
    
    try:
        await gateway.initialize()
        
        print("  正在查询可用模型...")
        models_response = await gateway.list_available_models()
        
        models = models_response.get("data", [])
        
        if models:
            print(f"  ✅ 找到 {len(models)} 个可用模型:")
            
            # 按提供商分组显示
            providers = {}
            for model in models:
                provider = model.get("provider", "unknown")
                if provider not in providers:
                    providers[provider] = []
                providers[provider].append(model)
            
            for provider, provider_models in providers.items():
                print(f"\n    📡 {provider.upper()}:")
                for model in provider_models:
                    status_emoji = "✅" if model.get("status") == "available" else "❌"
                    context_length = model.get("context_length", 0)
                    print(f"      {status_emoji} {model['id']} (上下文: {context_length} tokens)")
        else:
            print("  ⚠️ 没有找到可用模型")
    
    except Exception as e:
        print(f"  ❌ 查询失败: {e}")
    
    finally:
        await gateway.cleanup()


async def demo_engine_status():
    """演示引擎状态查询"""
    print("\n🔹 演示引擎状态查询")
    
    gateway = UnifiedAPIGateway()
    
    try:
        await gateway.initialize()
        
        print("  正在查询引擎状态...")
        status_response = await gateway.get_engines_status()
        
        engines = status_response.get("engines", {})
        
        if engines:
            print(f"  ✅ 找到 {len(engines)} 个引擎:")
            
            for engine_name, engine_status in engines.items():
                status = engine_status.get("status", "unknown")
                status_emoji = "✅" if status == "healthy" else "❌" if status == "error" else "⚠️"
                
                print(f"\n    {status_emoji} {engine_name.upper()} ({engine_status.get('provider', 'unknown')})")
                print(f"      状态: {status}")
                
                models_loaded = engine_status.get("models_loaded", [])
                if models_loaded:
                    print(f"      已加载模型: {', '.join(models_loaded)}")
                
                if engine_status.get("memory_usage_mb"):
                    print(f"      内存使用: {engine_status['memory_usage_mb']:.0f}MB")
                
                if engine_status.get("gpu_utilization"):
                    print(f"      GPU使用率: {engine_status['gpu_utilization']:.1f}%")
                
                if engine_status.get("error"):
                    print(f"      错误: {engine_status['error']}")
        else:
            print("  ⚠️ 没有找到引擎信息")
    
    except Exception as e:
        print(f"  ❌ 查询失败: {e}")
    
    finally:
        await gateway.cleanup()


async def demo_performance_stats():
    """演示性能统计"""
    print("\n🔹 演示性能统计")
    
    gateway = UnifiedAPIGateway()
    
    try:
        await gateway.initialize()
        
        # 先发送几个请求来生成统计数据
        print("  正在生成统计数据...")
        
        test_messages = [
            "你好",
            "今天天气怎么样？",
            "解释一下人工智能"
        ]
        
        for msg in test_messages:
            request = UnifiedChatRequest(
                model="auto",
                messages=[{"role": "user", "content": msg}],
                max_tokens=50
            )
            try:
                await gateway.handle_chat_completion(request)
            except:
                pass  # 忽略错误，继续统计
        
        # 获取性能统计
        print("  正在获取性能统计...")
        stats_response = await gateway.get_performance_stats()
        
        # 显示API网关统计
        api_stats = stats_response.get("api_gateway", {})
        print(f"\n  📊 API网关统计:")
        print(f"    总请求数: {api_stats.get('total_requests', 0)}")
        print(f"    成功请求: {api_stats.get('successful_requests', 0)}")
        print(f"    失败请求: {api_stats.get('failed_requests', 0)}")
        print(f"    平均延迟: {api_stats.get('avg_latency', 0):.0f}ms")
        
        # 显示按提供商的请求分布
        provider_stats = api_stats.get("requests_by_provider", {})
        if provider_stats:
            print(f"\n  📈 请求分布:")
            for provider, count in provider_stats.items():
                print(f"    {provider}: {count} 次")
        
        # 显示GPU信息
        gpu_info = stats_response.get("gpu_info", [])
        if gpu_info:
            print(f"\n  🎮 GPU信息:")
            for gpu in gpu_info:
                print(f"    GPU {gpu.get('id', 0)}: {gpu.get('name', 'Unknown')}")
                print(f"      使用率: {gpu.get('utilization', 0):.1f}%")
                print(f"      显存: {gpu.get('memory_used', 0)}/{gpu.get('memory_total', 0)}MB")
    
    except Exception as e:
        print(f"  ❌ 演示失败: {e}")
    
    finally:
        await gateway.cleanup()


async def demo_configuration():
    """演示配置管理"""
    print("\n🔹 演示配置管理")
    
    try:
        # 初始化配置管理器
        print("  正在初始化配置管理器...")
        await initialize_config_manager()
        
        # 获取当前配置
        print("  正在获取当前配置...")
        config = get_config()
        
        if config:
            print("  ✅ 配置加载成功")
            
            # 显示API配置
            api_config = config.get("api", {})
            print(f"\n  🌐 API配置:")
            print(f"    主机: {api_config.get('host', 'unknown')}")
            print(f"    端口: {api_config.get('port', 'unknown')}")
            
            # 显示启用的引擎
            engines_config = config.get("engines", {})
            enabled_engines = [name for name, cfg in engines_config.items() 
                             if cfg.get("enabled", False)]
            
            print(f"\n  🔧 启用的引擎: {', '.join(enabled_engines) if enabled_engines else '无'}")
            
            # 显示GPU配置
            gpu_config = config.get("gpu", {})
            print(f"\n  🎮 GPU配置:")
            print(f"    启用: {gpu_config.get('enabled', False)}")
            print(f"    GPU层数: {gpu_config.get('gpu_layers', 0)}")
            print(f"    自动检测: {gpu_config.get('auto_detect', False)}")
            
            # 显示路由配置
            routing_config = config.get("routing", {})
            print(f"\n  🧭 路由配置:")
            print(f"    策略: {routing_config.get('strategy', 'unknown')}")
            print(f"    本地偏好: {routing_config.get('local_preference', 0)}")
            print(f"    复杂度阈值: {routing_config.get('complexity_threshold', 0)}")
        else:
            print("  ⚠️ 配置为空或加载失败")
    
    except Exception as e:
        print(f"  ❌ 配置演示失败: {e}")


async def main():
    """主演示函数"""
    print("🚀 统一API系统演示")
    print("=" * 50)
    
    # 设置必要的环境变量（演示用）
    if not os.getenv("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = "demo_key_not_real"
    if not os.getenv("GEMINI_API_KEY"):
        os.environ["GEMINI_API_KEY"] = "demo_key_not_real"
    
    try:
        # 运行各个演示
        await demo_configuration()
        await demo_available_models()
        await demo_engine_status()
        await demo_basic_chat()
        await demo_model_selection()
        await demo_performance_stats()
        
        print("\n" + "=" * 50)
        print("✅ 演示完成！")
        print("\n📝 总结:")
        print("  - 统一API接口支持多种模型引擎")
        print("  - 智能路由根据任务复杂度选择最优模型")
        print("  - 动态配置管理支持实时更新")
        print("  - GPU加速自动检测和配置")
        print("  - 完整的性能监控和统计")
    
    except KeyboardInterrupt:
        print("\n\n⏹️ 演示被用户中断")
    except Exception as e:
        print(f"\n\n❌ 演示过程中发生错误: {e}")


if __name__ == "__main__":
    asyncio.run(main())