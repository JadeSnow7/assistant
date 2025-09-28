# CLI测试环境配置与构建部署设计

## 概述

本设计文档针对nex AI助手项目的CLI模式测试、环境配置、构建流程和GitHub部署进行全面规划。项目采用C++与Python混合架构，提供现代化CLI界面和Web GUI两种交互模式。

### 目标
- 建立完整的CLI测试环境配置流程
- 优化构建系统和部署流程
- 完善文档体系并准备GitHub发布
- 确保跨平台兼容性和稳定性

## 技术栈

### 核心技术栈
- **CLI框架**: Rich 13.7.0 + Textual 0.45.1
- **后端**: FastAPI 0.104.1 + Python 3.9+
- **C++核心**: C++20 + gRPC + Protobuf
- **AI模型**: qwen3:4b(本地) + Gemini Pro(云端)
- **构建工具**: CMake 3.20+ + 自定义shell脚本

### 依赖管理
```mermaid
graph TB
    subgraph "构建依赖"
        CMAKE[CMake 3.20+]
        GCC[GCC/Clang C++20]
        PYTHON[Python 3.9+]
        PIP[pip3]
    end
    
    subgraph "Python依赖"
        FASTAPI[FastAPI 0.104.1]
        RICH[Rich 13.7.0]
        TEXTUAL[Textual 0.45.1]
        GRPC[gRPC 1.59.0]
        TORCH[PyTorch 2.1.0]
    end
    
    subgraph "C++依赖"
        GRPCCPP[gRPC C++]
        PROTOBUF[Protobuf 4.25.0]
        CMAKE_DEPS[CMake查找包]
    end
```

## CLI架构设计

### 组件架构
```mermaid
flowchart TB
    subgraph "CLI启动层"
        START_CLI[start_cli.py<br/>简化启动器]
        MODERN_CLI[ui/cli/modern_cli.py<br/>现代化主控制器]
    end
    
    subgraph "CLI核心组件"
        COMMAND_ROUTER[命令路由器<br/>command_router.py]
        DISPLAY_ENGINE[显示引擎<br/>display_engine.py]
        SESSION_MGR[会话管理器<br/>session_manager.py]
        STREAM_DISPLAY[流式显示<br/>streaming_display.py]
    end
    
    subgraph "共享层"
        AI_CLIENT[AI客户端<br/>shared/ai_client.py]
        CONFIG[配置管理<br/>config.py]
    end
    
    subgraph "后端服务"
        FASTAPI_SRV[FastAPI服务<br/>python/main.py]
        GRPC_SRV[gRPC服务<br/>C++核心]
    end
    
    START_CLI --> AI_CLIENT
    MODERN_CLI --> COMMAND_ROUTER
    MODERN_CLI --> DISPLAY_ENGINE
    MODERN_CLI --> SESSION_MGR
    DISPLAY_ENGINE --> STREAM_DISPLAY
    
    COMMAND_ROUTER --> AI_CLIENT
    SESSION_MGR --> AI_CLIENT
    AI_CLIENT --> FASTAPI_SRV
    FASTAPI_SRV --> GRPC_SRV
```

### CLI启动模式对比
| 特性 | start_cli.py | ui/cli/modern_cli.py |
|------|-------------|---------------------|
| 复杂度 | 简化版本 | 完整版本 |
| 界面 | 基础命令行 | Rich现代化界面 |
| 功能 | 基本聊天 | 完整命令系统 |
| 适用场景 | 快速测试 | 生产使用 |

## 环境配置架构

### 配置层次结构
```mermaid
graph TD
    subgraph "环境配置层次"
        SYSTEM[系统环境<br/>OS + 编译工具]
        BUILD[构建环境<br/>CMake + 依赖库]
        RUNTIME[运行环境<br/>Python + 虚拟环境]
        SERVICE[服务配置<br/>端口 + 日志级别]
    end
    
    subgraph "配置文件"
        ENV_FILE[.env环境变量]
        REQUIREMENTS[requirements.txt]
        CMAKE_FILE[CMakeLists.txt]
        CONFIG_PY[python/core/config.py]
    end
    
    SYSTEM --> BUILD
    BUILD --> RUNTIME
    RUNTIME --> SERVICE
    
    ENV_FILE -.-> SERVICE
    REQUIREMENTS -.-> RUNTIME
    CMAKE_FILE -.-> BUILD
    CONFIG_PY -.-> SERVICE
```

### 环境变量管理
```mermaid
flowchart LR
    subgraph "环境变量优先级"
        CMDLINE[命令行参数]
        ENV_VAR[环境变量]
        CONFIG_FILE[配置文件]
        DEFAULT[默认值]
    end
    
    CMDLINE -->|最高优先级| ENV_VAR
    ENV_VAR --> CONFIG_FILE
    CONFIG_FILE --> DEFAULT
```

## 构建系统架构

### 构建流程设计
```mermaid
flowchart TD
    START[开始构建] --> CHECK_DEPS[检查依赖<br/>check_dependencies]
    CHECK_DEPS --> SETUP_DIR[创建构建目录<br/>setup_build_dir]
    SETUP_DIR --> BUILD_CPP[构建C++模块<br/>build_cpp]
    BUILD_CPP --> INSTALL_PY[安装Python依赖<br/>install_python_deps]
    INSTALL_PY --> VENV_CHECK{使用虚拟环境?}
    
    VENV_CHECK -->|是| CREATE_VENV[创建虚拟环境]
    VENV_CHECK -->|否| INSTALL_GLOBAL[全局安装]
    CREATE_VENV --> INSTALL_DEPS[安装依赖包]
    INSTALL_GLOBAL --> INSTALL_DEPS
    
    INSTALL_DEPS --> TEST_CHECK{运行测试?}
    TEST_CHECK -->|是| RUN_TESTS[运行测试套件]
    TEST_CHECK -->|否| BUILD_SUCCESS[构建完成]
    RUN_TESTS --> BUILD_SUCCESS
    
    subgraph "错误处理"
        ERROR[构建失败]
        CLEANUP[清理资源]
    end
    
    CHECK_DEPS -.->|失败| ERROR
    BUILD_CPP -.->|失败| ERROR
    INSTALL_DEPS -.->|失败| ERROR
    RUN_TESTS -.->|失败| ERROR
    ERROR --> CLEANUP
```

### 构建脚本参数设计
```bash
# scripts/build.sh 支持的参数
./scripts/build.sh [OPTIONS]

选项:
  --skip-tests     跳过测试阶段，加快构建速度
  --venv          启用Python虚拟环境
  --debug         启用调试模式构建
  --clean         清理旧的构建文件
  --parallel N    指定并行编译线程数
  --help          显示帮助信息
```

## 测试策略设计

### 测试层次架构
```mermaid
graph TB
    subgraph "测试金字塔"
        E2E[端到端测试<br/>CLI完整流程]
        INTEGRATION[集成测试<br/>组件交互]
        UNIT[单元测试<br/>独立组件]
    end
    
    subgraph "CLI专项测试"
        CLI_UNIT[CLI单元测试<br/>命令路由/显示引擎]
        CLI_INTEGRATION[CLI集成测试<br/>与后端交互]
        CLI_E2E[CLI端到端测试<br/>用户场景模拟]
    end
    
    subgraph "测试工具"
        PYTEST[pytest<br/>Python测试框架]
        MOCK[unittest.mock<br/>模拟组件]
        ASYNCIO_TEST[pytest-asyncio<br/>异步测试]
    end
    
    E2E --> CLI_E2E
    INTEGRATION --> CLI_INTEGRATION
    UNIT --> CLI_UNIT
    
    CLI_UNIT --> PYTEST
    CLI_INTEGRATION --> MOCK
    CLI_E2E --> ASYNCIO_TEST
```

### CLI测试用例设计
```mermaid
flowchart TD
    subgraph "命令测试用例"
        BASIC_CMD[基础命令测试]
        CHAT_CMD[聊天命令测试]
        SYS_CMD[系统命令测试]
        ERROR_CMD[错误处理测试]
    end
    
    subgraph "界面测试用例"
        DISPLAY_TEST[显示引擎测试]
        STREAM_TEST[流式显示测试]
        SESSION_TEST[会话管理测试]
        CONFIG_TEST[配置加载测试]
    end
    
    subgraph "集成测试用例"
        API_INTEGRATION[API集成测试]
        SERVICE_HEALTH[服务健康检查]
        ERROR_RECOVERY[错误恢复测试]
        PERFORMANCE[性能基准测试]
    end
```

## 服务启动架构

### 服务启动流程
```mermaid
sequenceDiagram
    participant User as 用户
    participant Script as run_server.sh
    participant CPP as C++服务
    participant Python as Python服务
    participant Health as 健康检查
    
    User->>Script: 启动服务
    Script->>Script: 创建必要目录
    Script->>Script: 检查端口占用
    Script->>CPP: 启动gRPC服务
    CPP-->>Script: 返回PID
    Script->>Script: 等待3秒
    Script->>Python: 启动FastAPI服务
    Python-->>Script: 返回PID
    Script->>Health: 执行健康检查
    Health->>CPP: 检查gRPC端口
    Health->>Python: 检查HTTP接口
    Health-->>Script: 返回检查结果
    Script-->>User: 显示服务信息
```

### 服务配置管理
```mermaid
graph LR
    subgraph "默认配置"
        HOST[Host: 0.0.0.0]
        PORT[Port: 8000]
        GRPC_PORT[gRPC Port: 50051]
        LOG_LEVEL[Log Level: INFO]
    end
    
    subgraph "可配置参数"
        HOST_CFG[--host HOST]
        PORT_CFG[--port PORT]
        GRPC_CFG[--grpc-port PORT]
        DEBUG_CFG[--debug]
        LOG_CFG[--log-level LEVEL]
    end
    
    subgraph "环境变量覆盖"
        ENV_HOST[HOST]
        ENV_PORT[PORT]
        ENV_GRPC[GRPC_PORT]
        ENV_DEBUG[DEBUG]
        ENV_LOG[LOG_LEVEL]
    end
    
    HOST_CFG -.-> HOST
    PORT_CFG -.-> PORT
    GRPC_CFG -.-> GRPC_PORT
    
    ENV_HOST -.-> HOST_CFG
    ENV_PORT -.-> PORT_CFG
    ENV_GRPC -.-> GRPC_CFG
```

## 文档体系设计

### 文档架构规划
```mermaid
flowchart TD
    subgraph "核心文档"
        README[README.md<br/>项目概述]
        QUICKSTART[QUICKSTART.md<br/>快速入门]
        CHANGELOG[CHANGELOG.md<br/>变更日志]
        CONTRIBUTING[CONTRIBUTING.md<br/>贡献指南]
    end
    
    subgraph "技术文档"
        API_DOC[docs/api.md<br/>API文档]
        PLUGIN_DOC[docs/plugins.md<br/>插件开发]
        DEPLOY_DOC[docs/deployment.md<br/>部署指南]
        ARCH_DOC[docs/architecture.md<br/>架构设计]
    end
    
    subgraph "用户指南"
        CLI_GUIDE[docs/cli-guide.md<br/>CLI使用指南]
        WEB_GUIDE[docs/web-guide.md<br/>Web界面指南]
        CONFIG_GUIDE[docs/configuration.md<br/>配置说明]
        FAQ[docs/faq.md<br/>常见问题]
    end
    
    subgraph "开发文档"
        DEV_GUIDE[docs/DEVELOPER_GUIDE.md<br/>开发者指南]
        BUILD_DOC[docs/build.md<br/>构建说明]
        TEST_DOC[docs/testing.md<br/>测试指南]
        RELEASE_DOC[docs/release.md<br/>发布流程]
    end
```

### 文档内容规范
```mermaid
graph TB
    subgraph "文档标准"
        STRUCTURE[统一结构<br/>标题层次]
        FORMAT[Markdown格式<br/>代码高亮]
        DIAGRAM[Mermaid图表<br/>架构可视化]
        EXAMPLES[示例代码<br/>操作演示]
    end
    
    subgraph "质量要求"
        ACCURACY[内容准确性]
        COMPLETENESS[完整性检查]
        READABILITY[可读性优化]
        MAINTENANCE[定期维护]
    end
```

## GitHub部署策略

### 仓库组织结构
```mermaid
flowchart TD
    subgraph "GitHub仓库"
        MAIN[main分支<br/>稳定版本]
        DEV[develop分支<br/>开发版本]
        FEATURE[feature/*<br/>功能分支]
        RELEASE[release/*<br/>发布分支]
    end
    
    subgraph "CI/CD工作流"
        BUILD_CI[构建测试<br/>.github/workflows/build.yml]
        TEST_CI[测试验证<br/>.github/workflows/test.yml]
        RELEASE_CI[发布流程<br/>.github/workflows/release.yml]
    end
    
    subgraph "发布管理"
        TAGS[版本标签<br/>v1.0.0]
        RELEASES[GitHub Releases<br/>发布说明]
        PACKAGES[GitHub Packages<br/>构建产物]
    end
    
    FEATURE --> DEV
    DEV --> RELEASE
    RELEASE --> MAIN
    
    MAIN --> BUILD_CI
    BUILD_CI --> TEST_CI
    TEST_CI --> RELEASE_CI
    
    RELEASE_CI --> TAGS
    TAGS --> RELEASES
    RELEASES --> PACKAGES
```

### GitHub Actions工作流
```mermaid
sequenceDiagram
    participant Dev as 开发者
    participant GitHub as GitHub
    participant CI as GitHub Actions
    participant Release as Release
    
    Dev->>GitHub: Push代码
    GitHub->>CI: 触发构建工作流
    
    CI->>CI: 环境检查
    CI->>CI: 依赖安装
    CI->>CI: C++编译
    CI->>CI: Python测试
    CI->>CI: CLI测试
    
    CI->>GitHub: 上传构建产物
    
    alt 发布版本
        Dev->>GitHub: 创建Release Tag
        GitHub->>Release: 触发发布工作流
        Release->>Release: 生成Release Notes
        Release->>Release: 打包分发文件
        Release->>GitHub: 发布Release
    end
```

## 部署配置设计

### 容器化部署
```mermaid
flowchart LR
    subgraph "Docker镜像构建"
        BASE[Ubuntu 22.04<br/>基础镜像]
        DEPS[安装构建依赖<br/>cmake, g++, python3]
        BUILD[构建C++模块<br/>cmake + make]
        PYTHON[安装Python依赖<br/>pip install]
    end
    
    subgraph "运行时配置"
        PORTS[暴露端口<br/>8000, 50051]
        VOLUMES[数据卷<br/>logs, data]
        ENV[环境变量<br/>配置参数]
        CMD[启动命令<br/>run_server.sh]
    end
    
    BASE --> DEPS
    DEPS --> BUILD
    BUILD --> PYTHON
    PYTHON --> PORTS
    PORTS --> VOLUMES
    VOLUMES --> ENV
    ENV --> CMD
```

### Kubernetes部署架构
```mermaid
graph TB
    subgraph "Kubernetes集群"
        subgraph "gRPC服务部署"
            GRPC_DEPLOY[Deployment<br/>C++后端服务]
            GRPC_SVC[Service<br/>内部负载均衡]
        end
        
        subgraph "API服务部署"
            API_DEPLOY[Deployment<br/>Python API服务]
            API_SVC[Service<br/>外部访问]
            INGRESS[Ingress<br/>HTTPS入口]
        end
        
        subgraph "配置管理"
            CONFIGMAP[ConfigMap<br/>应用配置]
            SECRET[Secret<br/>敏感信息]
        end
        
        subgraph "监控告警"
            HEALTH[健康检查探针]
            METRICS[指标收集]
            ALERTS[告警规则]
        end
    end
    
    CONFIGMAP -.-> GRPC_DEPLOY
    CONFIGMAP -.-> API_DEPLOY
    SECRET -.-> API_DEPLOY
    
    GRPC_DEPLOY --> GRPC_SVC
    API_DEPLOY --> API_SVC
    API_SVC --> INGRESS
    
    HEALTH -.-> GRPC_DEPLOY
    HEALTH -.-> API_DEPLOY
    METRICS -.-> GRPC_DEPLOY
    METRICS -.-> API_DEPLOY
```

## 性能优化设计

### CLI性能优化策略
```mermaid
flowchart TD
    subgraph "启动优化"
        LAZY_LOAD[懒加载组件<br/>按需初始化]
        CACHE_CONFIG[配置缓存<br/>减少文件读取]
        PARALLEL_INIT[并行初始化<br/>异步组件加载]
    end
    
    subgraph "运行时优化"
        STREAM_BUFFER[流式缓冲<br/>减少界面刷新]
        ASYNC_DISPLAY[异步显示<br/>非阻塞更新]
        MEMORY_POOL[内存池<br/>减少GC压力]
    end
    
    subgraph "网络优化"
        CONNECTION_POOL[连接池<br/>复用HTTP连接]
        REQUEST_BATCH[请求批处理<br/>减少网络调用]
        COMPRESSION[数据压缩<br/>减少传输量]
    end
```

### 构建性能优化
```mermaid
graph LR
    subgraph "并行构建"
        MAKE_J[make -j$(nproc)<br/>多线程编译]
        CCACHE[ccache<br/>编译缓存]
        NINJA[Ninja构建<br/>增量构建]
    end
    
    subgraph "依赖优化"
        PIP_CACHE[pip缓存<br/>避免重复下载]
        VENV_REUSE[虚拟环境复用<br/>开发环境]
        DOCKER_CACHE[Docker层缓存<br/>镜像构建]
    end
```

## 监控告警设计

### 系统监控架构
```mermaid
flowchart TD
    subgraph "监控指标"
        SYSTEM[系统指标<br/>CPU/内存/磁盘]
        SERVICE[服务指标<br/>响应时间/错误率]
        BUSINESS[业务指标<br/>会话数/请求量]
    end
    
    subgraph "数据收集"
        METRICS_API[/metrics接口<br/>Prometheus格式]
        LOG_COLLECT[日志收集<br/>结构化日志]
        HEALTH_CHECK[健康检查<br/>/health接口]
    end
    
    subgraph "告警策略"
        THRESHOLD[阈值告警<br/>CPU>80%]
        TREND[趋势告警<br/>错误率上升]
        AVAILABILITY[可用性告警<br/>服务下线]
    end
    
    SYSTEM --> METRICS_API
    SERVICE --> LOG_COLLECT
    BUSINESS --> HEALTH_CHECK
    
    METRICS_API --> THRESHOLD
    LOG_COLLECT --> TREND
    HEALTH_CHECK --> AVAILABILITY
```

## 错误处理与恢复

### 错误处理流程
```mermaid
flowchart TD
    ERROR[错误发生] --> DETECT[错误检测]
    DETECT --> CLASSIFY[错误分类]
    
    CLASSIFY --> RECOVERABLE{可恢复?}
    RECOVERABLE -->|是| AUTO_RECOVERY[自动恢复]
    RECOVERABLE -->|否| GRACEFUL_SHUTDOWN[优雅关闭]
    
    AUTO_RECOVERY --> RETRY[重试机制]
    RETRY --> SUCCESS{恢复成功?}
    SUCCESS -->|是| NORMAL[正常运行]
    SUCCESS -->|否| ESCALATE[问题升级]
    
    GRACEFUL_SHUTDOWN --> CLEANUP[资源清理]
    ESCALATE --> ADMIN_NOTIFY[管理员通知]
    CLEANUP --> EXIT[安全退出]
```

### CLI错误恢复策略
```mermaid
graph TB
    subgraph "连接错误"
        CONN_FAIL[连接失败]
        RETRY_CONN[重试连接]
        OFFLINE_MODE[离线模式]
    end
    
    subgraph "命令错误"
        CMD_ERROR[命令执行错误]
        ERROR_MSG[友好错误提示]
        HELP_SUGGEST[帮助建议]
    end
    
    subgraph "系统错误"
        SYS_ERROR[系统级错误]
        SAFE_EXIT[安全退出]
        STATE_SAVE[状态保存]
    end
    
    CONN_FAIL --> RETRY_CONN
    RETRY_CONN --> OFFLINE_MODE
    
    CMD_ERROR --> ERROR_MSG
    ERROR_MSG --> HELP_SUGGEST
    
    SYS_ERROR --> STATE_SAVE
    STATE_SAVE --> SAFE_EXIT
```

## 实施路线图

### 开发阶段规划
```mermaid
gantt
    title 实施时间线
    dateFormat  YYYY-MM-DD
    section 阶段1: 环境配置
    依赖检查优化           :a1, 2024-01-01, 3d
    构建脚本增强           :a2, after a1, 5d
    虚拟环境管理           :a3, after a2, 3d
    
    section 阶段2: CLI测试
    单元测试编写           :b1, after a3, 7d
    集成测试开发           :b2, after b1, 5d
    端到端测试设计         :b3, after b2, 3d
    
    section 阶段3: 文档完善
    技术文档编写           :c1, after b3, 10d
    用户指南创建           :c2, after c1, 7d
    API文档生成           :c3, after c2, 3d
    
    section 阶段4: GitHub部署
    CI/CD配置             :d1, after c3, 5d
    Release流程           :d2, after d1, 3d
    容器化部署            :d3, after d2, 5d
```

### 验收标准

#### 功能验收
- ✅ CLI启动正常，界面显示完整
- ✅ 所有基础命令响应正确
- ✅ 流式显示功能稳定
- ✅ 错误处理机制有效
- ✅ 会话管理功能正常

#### 性能验收
- ✅ 启动时间 < 3秒
- ✅ 命令响应时间 < 500ms
- ✅ 内存使用 < 200MB
- ✅ CPU使用率 < 50%

#### 稳定性验收
- ✅ 长时间运行无内存泄漏
- ✅ 网络异常自动恢复
- ✅ 服务重启后状态保持
- ✅ 并发测试通过

#### 兼容性验收
- ✅ Linux/macOS/Windows跨平台支持
- ✅ Python 3.9-3.12版本兼容
- ✅ 不同终端环境正常显示
- ✅ Docker容器化运行正常

## 测试用例设计

### CLI功能测试矩阵

| 测试场景 | 测试用例 | 预期结果 | 优先级 |
|---------|---------|---------|--------|
| 基础启动 | 执行start_cli.py | 显示欢迎界面，连接服务 | P0 |
| 现代化CLI | 执行modern_cli.py | Rich界面正常，命令提示符显示 | P0 |
| 健康检查 | 服务未启动时运行CLI | 显示连接异常警告，继续运行 | P1 |
| 基础聊天 | 输入"你好" | AI回复正常，显示模型信息 | P0 |
| 流式显示 | 输入长文本请求 | 实时显示生成内容，进度指示 | P1 |
| 命令路由 | 输入/help命令 | 显示帮助信息，格式正确 | P0 |
| 会话管理 | 多轮对话 | 上下文保持，会话ID不变 | P1 |
| 错误处理 | 输入无效命令 | 友好错误提示，建议帮助 | P1 |
| 退出机制 | 按Ctrl+C或/exit | 优雅退出，资源清理 | P0 |
| 配置加载 | 修改配置文件 | 配置生效，参数正确读取 | P2 |

### 自动化测试脚本设计

```bash
#!/bin/bash
# tests/cli_integration_test.sh

echo "🧪 开始CLI集成测试"

# 1. 环境检查
test_environment() {
    echo "📋 检查测试环境..."
    python3 --version || exit 1
    pip3 show rich || exit 1
    pip3 show fastapi || exit 1
}

# 2. 服务启动测试
test_service_startup() {
    echo "🚀 测试服务启动..."
    timeout 30 ./scripts/run_server.sh --debug &
    SERVER_PID=$!
    sleep 10
    
    # 检查服务是否启动
    curl -s http://localhost:8000/health || {
        echo "❌ 服务启动失败"
        kill $SERVER_PID
        exit 1
    }
    
    echo "✅ 服务启动成功"
}

# 3. CLI启动测试
test_cli_startup() {
    echo "💻 测试CLI启动..."
    
    # 测试简化版CLI
    timeout 10 python3 start_cli.py <<< "quit" || {
        echo "❌ 简化CLI启动失败"
        exit 1
    }
    
    # 测试现代化CLI
    timeout 10 python3 ui/cli/modern_cli.py <<< "/exit" || {
        echo "❌ 现代化CLI启动失败"
        exit 1
    }
    
    echo "✅ CLI启动测试通过"
}

# 4. 功能测试
test_cli_functions() {
    echo "⚙️ 测试CLI功能..."
    
    # 创建测试脚本
    cat > /tmp/cli_test_input.txt << EOF
你好
/help
/status
测试流式响应功能
/exit
EOF
    
    timeout 60 python3 ui/cli/modern_cli.py < /tmp/cli_test_input.txt > /tmp/cli_test_output.log 2>&1
    
    # 检查输出
    grep -q "AI Assistant" /tmp/cli_test_output.log || {
        echo "❌ 欢迎界面未显示"
        exit 1
    }
    
    echo "✅ CLI功能测试通过"
}

# 5. 清理资源
cleanup() {
    echo "🧹 清理测试资源..."
    pkill -f "run_server.sh" || true
    pkill -f "uvicorn" || true
    pkill -f "ai_assistant_server" || true
    rm -f /tmp/cli_test_*
}

# 主测试流程
main() {
    trap cleanup EXIT
    
    test_environment
    test_service_startup
    test_cli_startup
    test_cli_functions
    
    echo "🎉 所有测试通过！"
}

main "$@"
```

## 环境配置实施方案

### 开发环境快速配置

```bash
#!/bin/bash
# scripts/setup_dev_env.sh

echo "🔧 配置开发环境"

# 检查系统类型
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
    elif [[ "$OSTYPE" == "msys" ]]; then
        OS="windows"
    else
        echo "❌ 不支持的操作系统: $OSTYPE"
        exit 1
    fi
    echo "📱 检测到操作系统: $OS"
}

# 安装系统依赖
install_system_deps() {
    echo "📦 安装系统依赖..."
    
    case $OS in
        "linux")
            sudo apt-get update
            sudo apt-get install -y cmake build-essential python3-dev python3-pip python3-venv
            ;;
        "macos")
            brew install cmake python@3.9
            ;;
        "windows")
            echo "请手动安装: CMake, Visual Studio Build Tools, Python 3.9+"
            ;;
    esac
}

# 创建Python虚拟环境
setup_python_env() {
    echo "🐍 设置Python环境..."
    
    # 创建虚拟环境
    python3 -m venv venv
    
    # 激活虚拟环境
    source venv/bin/activate
    
    # 升级pip
    pip install --upgrade pip
    
    # 安装依赖
    pip install -r requirements.txt
    
    echo "✅ Python环境配置完成"
}

# 验证环境
verify_environment() {
    echo "🔍 验证环境配置..."
    
    # 检查Python环境
    python3 -c "import fastapi, rich, textual" || {
        echo "❌ Python依赖验证失败"
        exit 1
    }
    
    # 检查构建工具
    cmake --version || {
        echo "❌ CMake未正确安装"
        exit 1
    }
    
    echo "✅ 环境验证通过"
}

# 主函数
main() {
    detect_os
    install_system_deps
    setup_python_env
    verify_environment
    
    echo "🎉 开发环境配置完成！"
    echo "📝 下一步:"
    echo "   1. 激活虚拟环境: source venv/bin/activate"
    echo "   2. 构建项目: ./scripts/build.sh --venv"
    echo "   3. 启动服务: ./scripts/run_server.sh"
    echo "   4. 测试CLI: python start_cli.py"
}

main "$@"
```

### 生产环境部署配置

```dockerfile
# Dockerfile.production
FROM ubuntu:22.04

# 设置环境变量
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHON_VERSION=3.10
ENV APP_HOME=/app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    python3.10 \
    python3.10-dev \
    python3.10-venv \
    python3-pip \
    curl \
    wget \
    git \
    && rm -rf /var/lib/apt/lists/*

# 创建应用目录
WORKDIR $APP_HOME

# 复制项目文件
COPY requirements.txt .
COPY CMakeLists.txt .
COPY cpp/ ./cpp/
COPY python/ ./python/
COPY scripts/ ./scripts/
COPY ui/ ./ui/
COPY protos/ ./protos/

# 构建应用
RUN pip3 install --no-cache-dir -r requirements.txt
RUN mkdir build && cd build && \
    cmake .. -DCMAKE_BUILD_TYPE=Release && \
    make -j$(nproc) && \
    make install

# 创建非root用户
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser $APP_HOME
USER appuser

# 创建必要目录
RUN mkdir -p logs data python/plugins

# 暴露端口
EXPOSE 8000 50051

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
CMD ["./scripts/run_server.sh"]
```

## GitHub Actions工作流配置

### 构建测试工作流

```yaml
# .github/workflows/ci.yml
name: 构建测试

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-22.04, macos-latest]
        python-version: ["3.9", "3.10", "3.11"]
    
    steps:
    - uses: actions/checkout@v4
    
    - name: 设置Python环境
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: 安装系统依赖
      run: |
        if [ "$RUNNER_OS" == "Linux" ]; then
          sudo apt-get update
          sudo apt-get install -y cmake build-essential
        elif [ "$RUNNER_OS" == "macOS" ]; then
          brew install cmake
        fi
    
    - name: 缓存Python依赖
      uses: actions/cache@v3
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}
    
    - name: 安装Python依赖
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-asyncio pytest-cov
    
    - name: 构建C++模块
      run: |
        mkdir build
        cd build
        cmake .. -DCMAKE_BUILD_TYPE=Release
        make -j$(nproc 2>/dev/null || echo 2)
    
    - name: 运行Python测试
      run: |
        pytest tests/ -v --cov=python --cov-report=xml
    
    - name: 运行CLI集成测试
      run: |
        chmod +x tests/cli_integration_test.sh
        ./tests/cli_integration_test.sh
    
    - name: 上传覆盖率报告
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: unittests
        name: codecov-umbrella

  docker-build:
    runs-on: ubuntu-latest
    needs: test
    
    steps:
    - uses: actions/checkout@v4
    
    - name: 构建Docker镜像
      run: |
        docker build -f Dockerfile.production -t ai-assistant:latest .
    
    - name: 测试Docker镜像
      run: |
        docker run --rm -d --name test-container -p 8000:8000 ai-assistant:latest
        sleep 30
        curl -f http://localhost:8000/health
        docker stop test-container
```

### 发布工作流

```yaml
# .github/workflows/release.yml
name: 发布版本

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
      with:
        fetch-depth: 0
    
    - name: 设置Python环境
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    
    - name: 构建项目
      run: |
        ./scripts/build.sh --skip-tests
    
    - name: 生成变更日志
      id: changelog
      run: |
        echo "## 更新内容" > RELEASE_NOTES.md
        git log $(git describe --tags --abbrev=0 HEAD^)..HEAD --pretty=format:"- %s" >> RELEASE_NOTES.md
    
    - name: 创建发布包
      run: |
        tar -czf ai-assistant-${{ github.ref_name }}.tar.gz \
          --exclude='.git*' \
          --exclude='venv' \
          --exclude='build' \
          --exclude='__pycache__' \
          .
    
    - name: 构建Docker镜像
      run: |
        docker build -f Dockerfile.production -t ai-assistant:${{ github.ref_name }} .
        docker save ai-assistant:${{ github.ref_name }} | gzip > ai-assistant-docker-${{ github.ref_name }}.tar.gz
    
    - name: 创建GitHub Release
      uses: softprops/action-gh-release@v1
      with:
        body_path: RELEASE_NOTES.md
        files: |
          ai-assistant-${{ github.ref_name }}.tar.gz
          ai-assistant-docker-${{ github.ref_name }}.tar.gz
        draft: false
        prerelease: false
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## 性能基准测试

### CLI性能测试

```python
# tests/performance/cli_benchmark.py
import asyncio
import time
import psutil
import pytest
from ui.cli.modern_cli import ModernCLI
from ui.shared.ai_client import EnhancedAIClient

class CLIPerformanceBenchmark:
    def __init__(self):
        self.cli = None
        self.process = psutil.Process()
    
    async def setup(self):
        """初始化测试环境"""
        self.cli = ModernCLI("http://localhost:8000")
        # 预热
        await self.cli.client.health_check()
    
    @pytest.mark.asyncio
    async def test_startup_time(self):
        """测试启动时间"""
        start_time = time.time()
        
        cli = ModernCLI("http://localhost:8000")
        await cli._initialize_session()
        
        startup_time = time.time() - start_time
        
        assert startup_time < 3.0, f"启动时间过长: {startup_time:.2f}s"
        print(f"✅ 启动时间: {startup_time:.2f}s")
    
    @pytest.mark.asyncio
    async def test_memory_usage(self):
        """测试内存使用"""
        initial_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        
        # 执行100次聊天命令
        for i in range(100):
            await self.cli.process_user_input(f"测试消息 {i}")
        
        final_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        assert memory_increase < 50, f"内存增长过多: {memory_increase:.2f}MB"
        print(f"✅ 内存增长: {memory_increase:.2f}MB")
    
    @pytest.mark.asyncio
    async def test_command_response_time(self):
        """测试命令响应时间"""
        response_times = []
        
        for i in range(50):
            start_time = time.time()
            await self.cli.process_user_input("/status")
            response_time = time.time() - start_time
            response_times.append(response_time)
        
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)
        
        assert avg_response_time < 0.5, f"平均响应时间过长: {avg_response_time:.3f}s"
        assert max_response_time < 1.0, f"最大响应时间过长: {max_response_time:.3f}s"
        
        print(f"✅ 平均响应时间: {avg_response_time:.3f}s")
        print(f"✅ 最大响应时间: {max_response_time:.3f}s")
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """测试并发请求处理"""
        async def send_request(i):
            start_time = time.time()
            await self.cli.process_user_input(f"并发测试 {i}")
            return time.time() - start_time
        
        # 并发发送10个请求
        tasks = [send_request(i) for i in range(10)]
        response_times = await asyncio.gather(*tasks)
        
        avg_concurrent_time = sum(response_times) / len(response_times)
        
        assert avg_concurrent_time < 2.0, f"并发响应时间过长: {avg_concurrent_time:.3f}s"
        print(f"✅ 并发平均响应时间: {avg_concurrent_time:.3f}s")

if __name__ == "__main__":
    async def main():
        benchmark = CLIPerformanceBenchmark()
        await benchmark.setup()
        
        await benchmark.test_startup_time()
        await benchmark.test_memory_usage()
        await benchmark.test_command_response_time()
        await benchmark.test_concurrent_requests()
        
        print("🎉 性能测试完成")
    
    asyncio.run(main())
```