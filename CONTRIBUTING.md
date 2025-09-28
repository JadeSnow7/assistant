# 贡献指南

感谢您对 AI Assistant 项目的关注！我们欢迎所有形式的贡献，包括但不限于代码贡献、文档改进、问题报告和功能建议。

## 🤝 参与方式

### 1. 代码贡献
- 实现新功能
- 修复 Bug
- 性能优化
- 代码重构

### 2. 文档贡献  
- 改进现有文档
- 添加使用示例
- 翻译文档
- 编写教程

### 3. 社区参与
- 回答问题
- 分享使用经验
- 提供反馈建议
- 推广项目

## 🚀 开始贡献

### 开发环境设置

1. **Fork 项目**
   ```bash
   # 在 GitHub 上 Fork 项目到你的账户
   git clone https://github.com/your-username/ai-assistant.git
   cd ai-assistant
   ```

2. **设置上游仓库**
   ```bash
   git remote add upstream https://github.com/original-repo/ai-assistant.git
   ```

3. **创建虚拟环境**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Linux/Mac
   # venv\Scripts\activate    # Windows
   ```

4. **安装依赖**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

5. **运行测试**
   ```bash
   pytest tests/
   ```

### 开发流程

1. **创建分支**
   ```bash
   git checkout -b feature/your-feature-name
   # 或
   git checkout -b fix/your-bug-fix
   ```

2. **进行开发**
   - 遵循代码规范
   - 添加必要的测试
   - 更新相关文档

3. **提交代码**
   ```bash
   git add .
   git commit -m "feat: 添加新功能描述"
   ```

4. **推送到 GitHub**
   ```bash
   git push origin feature/your-feature-name
   ```

5. **创建 Pull Request**
   - 详细描述你的更改
   - 关联相关的 Issue
   - 等待代码审查

## 📋 代码规范

### Python 代码规范

我们遵循 [PEP 8](https://pep8.org/) 和 [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)。

**代码格式化工具**:
```bash
# 使用 black 格式化代码
black src/

# 使用 isort 整理导入
isort src/

# 使用 flake8 检查代码质量
flake8 src/
```

**示例代码风格**:
```python
"""模块文档字符串."""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ExampleClass:
    """类文档字符串."""
    
    def __init__(self, param: str) -> None:
        """初始化方法."""
        self.param = param
    
    def example_method(self, data: Dict[str, Any]) -> Optional[str]:
        """
        示例方法.
        
        Args:
            data: 输入数据字典
            
        Returns:
            处理结果字符串，失败时返回 None
        """
        try:
            # 业务逻辑
            result = self._process_data(data)
            return result
        except Exception as e:
            logger.error(f"处理数据失败: {e}")
            return None
```

### C++ 代码规范

遵循 [Google C++ Style Guide](https://google.github.io/styleguide/cppguide.html)。

**示例代码风格**:
```cpp
#include "model_engine.hpp"
#include <memory>
#include <string>

namespace ai_assistant {

class ModelEngine {
public:
    explicit ModelEngine(const Config& config);
    ~ModelEngine() = default;
    
    // 禁用拷贝构造和赋值
    ModelEngine(const ModelEngine&) = delete;
    ModelEngine& operator=(const ModelEngine&) = delete;
    
    // 加载模型
    bool LoadModel(const std::string& model_path);
    
    // 推理接口
    std::string Inference(const std::string& input) const;

private:
    Config config_;
    std::unique_ptr<Model> model_;
    
    // 私有方法使用下划线后缀
    void InitializeModel_();
};

}  // namespace ai_assistant
```

## 🧪 测试规范

### 测试要求
- 新功能必须包含单元测试
- 测试覆盖率应保持在 80% 以上
- 集成测试覆盖主要业务流程

### 测试结构
```
tests/
├── unit/                  # 单元测试
│   ├── test_orchestrator.py
│   ├── test_cloud_client.py
│   └── test_memory_manager.py
├── integration/           # 集成测试
│   ├── test_api_endpoints.py
│   └── test_plugin_system.py
└── fixtures/             # 测试数据
    ├── sample_requests.json
    └── mock_responses.json
```

### 测试示例
```python
import pytest
from unittest.mock import Mock, patch
from python.core.cloud_client import CloudClient


class TestCloudClient:
    """云端客户端测试类."""
    
    @pytest.fixture
    def cloud_client(self):
        """创建测试用客户端."""
        config = {
            "gemini_api_key": "test-key",
            "model_type": "gemini"
        }
        return CloudClient(config)
    
    @pytest.mark.asyncio
    async def test_chat_completion_success(self, cloud_client):
        """测试聊天接口成功场景."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            # 模拟成功响应
            mock_response = Mock()
            mock_response.status = 200
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "Hello!"}}]
            }
            mock_post.return_value.__aenter__.return_value = mock_response
            
            # 执行测试
            result = await cloud_client.chat_completion([
                {"role": "user", "content": "Hi"}
            ])
            
            # 验证结果
            assert result["content"] == "Hello!"
            mock_post.assert_called_once()
```

## 📝 提交消息规范

我们使用 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

### 格式
```
<类型>[可选的作用域]: <描述>

[可选的正文]

[可选的脚注]
```

### 类型说明
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式（不影响代码运行的变动）
- `refactor`: 重构（既不是新增功能，也不是修改bug的代码变动）
- `perf`: 性能优化
- `test`: 增加测试
- `chore`: 构建过程或辅助工具的变动

### 示例
```bash
git commit -m "feat: 添加天气查询插件"
git commit -m "fix: 修复内存泄漏问题"
git commit -m "docs: 更新API文档"
git commit -m "refactor: 重构模型加载逻辑"
```

## 🐛 问题报告

### 报告 Bug
使用 GitHub Issues，请包含以下信息：

1. **环境信息**
   - 操作系统和版本
   - Python 版本
   - 项目版本

2. **问题描述**
   - 预期行为
   - 实际行为
   - 重现步骤

3. **日志信息**
   ```bash
   # 提供相关日志
   tail -f logs/app.log
   ```

### 功能请求
1. 详细描述需求场景
2. 说明期望的解决方案
3. 考虑替代方案
4. 评估实现复杂度

## 📖 文档贡献

### 文档类型
- **API 文档**: 接口说明和示例
- **用户指南**: 使用教程和最佳实践
- **开发文档**: 架构设计和技术细节
- **部署文档**: 安装和运维指南

### 文档规范
- 使用 Markdown 格式
- 包含代码示例
- 提供清晰的步骤说明
- 定期更新维护

## 🎯 优先级项目

当前急需贡献的领域：

### 高优先级
- [ ] C++ gRPC 服务端实现
- [ ] Web UI 界面开发
- [ ] 性能测试和优化
- [ ] 安全审计和加固

### 中优先级
- [ ] 更多插件开发
- [ ] 多语言支持
- [ ] 监控面板
- [ ] API 文档完善

### 低优先级
- [ ] 移动端适配
- [ ] 桌面客户端
- [ ] 云原生部署
- [ ] 微服务架构

## 🏆 贡献者认可

我们重视每一个贡献者的努力：

- **代码贡献者**: 在 README 中列出
- **文档贡献者**: 在文档中署名
- **问题报告者**: 在 CHANGELOG 中感谢
- **长期贡献者**: 邀请成为项目维护者

## 📞 联系我们

- **GitHub Issues**: 技术问题和功能请求
- **GitHub Discussions**: 社区讨论
- **Email**: dev@ai-assistant.com
- **Slack**: [加入我们的 Slack](https://join.slack.com/t/ai-assistant)

## 📄 许可证

通过贡献代码，您同意您的贡献将在 [MIT 许可证](LICENSE) 下发布。

---

**感谢您的贡献！** 🎉

每一个贡献都让 AI Assistant 变得更好。我们期待与您一起构建智能化的未来！