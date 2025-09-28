#!/usr/bin/env python3
"""
测试框架验证脚本
快速验证测试框架是否正确部署和配置
"""
import sys
import os
import asyncio
import time
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "tests"))
sys.path.insert(0, str(project_root / "python"))

async def verify_test_framework():
    """验证测试框架"""
    print("🧪 AI助手测试框架验证")
    print("=" * 50)
    
    verification_results = []
    
    # 1. 验证测试基础类
    try:
        from tests.base import BaseTestSuite, TestCase, TestResult, TestMetrics
        print("✅ 基础测试类导入成功")
        verification_results.append(True)
    except Exception as e:
        print(f"❌ 基础测试类导入失败: {e}")
        verification_results.append(False)
    
    # 2. 验证对话系统测试
    try:
        from tests.unit.test_dialog_system import DialogSystemTestSuite
        print("✅ 对话系统测试套件导入成功")
        verification_results.append(True)
    except Exception as e:
        print(f"❌ 对话系统测试套件导入失败: {e}")
        verification_results.append(False)
    
    # 3. 验证智能路由测试
    try:
        from tests.unit.test_intelligent_routing import IntelligentRoutingTestSuite
        print("✅ 智能路由测试套件导入成功")
        verification_results.append(True)
    except Exception as e:
        print(f"❌ 智能路由测试套件导入失败: {e}")
        verification_results.append(False)
    
    # 4. 验证系统指令测试
    try:
        from tests.unit.test_system_commands import SystemCommandTestSuite
        print("✅ 系统指令测试套件导入成功")
        verification_results.append(True)
    except Exception as e:
        print(f"❌ 系统指令测试套件导入失败: {e}")
        verification_results.append(False)
    
    # 5. 验证资源管理测试
    try:
        from tests.unit.test_resource_management import ResourceManagementTestSuite
        print("✅ 资源管理测试套件导入成功")
        verification_results.append(True)
    except Exception as e:
        print(f"❌ 资源管理测试套件导入失败: {e}")
        verification_results.append(False)
    
    # 6. 验证端到端测试
    try:
        from tests.e2e.test_integration_flows import EndToEndIntegrationTestSuite
        print("✅ 端到端集成测试套件导入成功")
        verification_results.append(True)
    except Exception as e:
        print(f"❌ 端到端集成测试套件导入失败: {e}")
        verification_results.append(False)
    
    # 7. 验证自动化测试运行器
    try:
        from tests.test_runner import AutomatedTestRunner
        print("✅ 自动化测试运行器导入成功")
        verification_results.append(True)
    except Exception as e:
        print(f"❌ 自动化测试运行器导入失败: {e}")
        verification_results.append(False)
    
    # 8. 验证测试用例创建
    try:
        test_case = TestCase(
            name="verification_test",
            description="验证测试用例创建",
            input_data={"message": "测试"},
            expected_output={"success": True},
            category="验证",
            priority="HIGH"
        )
        print("✅ 测试用例创建成功")
        verification_results.append(True)
    except Exception as e:
        print(f"❌ 测试用例创建失败: {e}")
        verification_results.append(False)
    
    # 9. 验证测试指标
    try:
        metrics = TestMetrics(
            response_time_ms=100,
            token_count=50,
            model_used="test_model",
            memory_usage_mb=10.0,
            cpu_usage_percent=5.0,
            success=True
        )
        print("✅ 测试指标创建成功")
        verification_results.append(True)
    except Exception as e:
        print(f"❌ 测试指标创建失败: {e}")
        verification_results.append(False)
    
    # 10. 验证测试套件初始化
    try:
        base_suite = BaseTestSuite("http://localhost:8000")
        print("✅ 基础测试套件初始化成功")
        verification_results.append(True)
    except Exception as e:
        print(f"❌ 基础测试套件初始化失败: {e}")
        verification_results.append(False)
    
    print("\n" + "=" * 50)
    
    # 统计结果
    success_count = sum(verification_results)
    total_count = len(verification_results)
    success_rate = (success_count / total_count) * 100
    
    print(f"📊 验证结果统计:")
    print(f"   成功: {success_count}/{total_count}")
    print(f"   成功率: {success_rate:.1f}%")
    
    if success_rate >= 90:
        print("🎉 测试框架验证通过！")
        print("\n📝 后续步骤:")
        print("   1. 启动AI助手服务: ./scripts/run_server.sh")
        print("   2. 运行基础测试: ./scripts/run_tests.sh quick")
        print("   3. 运行完整测试: ./scripts/run_tests.sh")
        return True
    else:
        print("⚠️ 测试框架验证未完全通过，请检查导入错误")
        return False

def verify_file_structure():
    """验证文件结构"""
    print("\n📁 验证测试文件结构")
    print("-" * 30)
    
    required_files = [
        "tests/__init__.py",
        "tests/base.py", 
        "tests/unit/test_dialog_system.py",
        "tests/unit/test_intelligent_routing.py",
        "tests/unit/test_system_commands.py",
        "tests/unit/test_resource_management.py",
        "tests/e2e/test_integration_flows.py",
        "tests/test_runner.py",
        "scripts/run_tests.sh",
        "docs/TESTING_GUIDE.md"
    ]
    
    missing_files = []
    
    for file_path in required_files:
        full_path = project_root / file_path
        if full_path.exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} (缺失)")
            missing_files.append(file_path)
    
    if not missing_files:
        print("\n🎯 所有必需文件都存在")
        return True
    else:
        print(f"\n⚠️ 缺失 {len(missing_files)} 个文件")
        return False

def check_dependencies():
    """检查依赖包"""
    print("\n📦 检查依赖包")
    print("-" * 20)
    
    required_packages = [
        "asyncio",
        "aiohttp", 
        "time",
        "json",
        "logging",
        "dataclasses",
        "typing",
        "pathlib"
    ]
    
    optional_packages = [
        "psutil"  # 用于系统资源监控
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} (缺失)")
            missing_packages.append(package)
    
    for package in optional_packages:
        try:
            __import__(package)
            print(f"✅ {package} (可选)")
        except ImportError:
            print(f"⚠️ {package} (可选，建议安装)")
    
    if not missing_packages:
        print("\n📚 所有必需依赖都可用")
        return True
    else:
        print(f"\n⚠️ 缺失 {len(missing_packages)} 个必需依赖")
        print("请运行: pip install " + " ".join(missing_packages))
        return False

async def main():
    """主函数"""
    print("🚀 开始AI助手测试框架验证")
    print("时间:", time.strftime("%Y-%m-%d %H:%M:%S"))
    
    # 检查文件结构
    file_structure_ok = verify_file_structure()
    
    # 检查依赖
    dependencies_ok = check_dependencies()
    
    # 验证测试框架
    framework_ok = await verify_test_framework()
    
    print("\n" + "=" * 60)
    print("🏁 验证完成")
    
    if file_structure_ok and dependencies_ok and framework_ok:
        print("✅ 测试框架已就绪，可以开始测试！")
        print("\n🎯 快速开始:")
        print("   # 基础健康检查")
        print("   ./scripts/run_tests.sh quick")
        print("   ")
        print("   # 运行完整测试套件")  
        print("   ./scripts/run_tests.sh")
        print("   ")
        print("   # 生成HTML报告")
        print("   ./scripts/run_tests.sh -f html")
        return 0
    else:
        print("❌ 测试框架验证失败，请根据上述提示修复问题")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️ 验证被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 验证过程发生异常: {e}")
        sys.exit(1)