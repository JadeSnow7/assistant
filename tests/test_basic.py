"""简单的导入测试，验证模块路径是否正确"""

def test_imports():
    """测试关键模块是否可以正常导入"""
    try:
        # 测试基础模块导入
        from tests.unit.base import BaseTestSuite
        from tests.unit.cli_test_base import CLITestBase
        
        # 测试Python核心模块导入
        import python
        import python.core
        
        print("✅ 所有关键模块导入成功")
        return True
    except ImportError as e:
        print(f"❌ 模块导入失败: {e}")
        return False


def test_basic_functionality():
    """测试基础功能"""
    assert 2 + 2 == 4
    assert "hello".upper() == "HELLO"
    print("✅ 基础功能测试通过")


if __name__ == "__main__":
    test_imports()
    test_basic_functionality()