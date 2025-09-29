"""
NEX AI Assistant - 主入口文件
使用重构后的模块化架构
"""
import asyncio
import logging
import uvicorn
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# 使用新的模块结构
from services.agent.orchestrator import AgentOrchestrator
from services.agent.api_router import api_router
from services.agent.websocket_handler import websocket_router
from core.foundation.config.config import settings
from core.foundation.grpc_client import GRPCClient
from services.memory.memory_manager import MemoryManager
from services.plugin.plugin_manager import PluginManager
from core.foundation.cloud_client import CloudClient


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    logger.info("🚀 启动NEX AI Assistant服务...")
    
    try:
        # 初始化gRPC客户端
        grpc_client = GRPCClient(settings.grpc_server_address)
        await grpc_client.connect()
        app.state.grpc_client = grpc_client
        
        # 初始化记忆管理器
        memory_manager = MemoryManager()
        await memory_manager.initialize()
        app.state.memory_manager = memory_manager
        
        # 初始化插件管理器
        plugin_manager = PluginManager()
        await plugin_manager.initialize()
        app.state.plugin_manager = plugin_manager
        
        # 初始化Agent调度器
        orchestrator = AgentOrchestrator(
            grpc_client=grpc_client,
            memory_manager=memory_manager,
            plugin_manager=plugin_manager
        )
        await orchestrator.initialize()
        app.state.orchestrator = orchestrator
        
        logger.info("✅ NEX AI Assistant服务启动完成")
        
    except Exception as e:
        logger.error(f"❌ 服务启动失败: {e}")
        raise
    
    yield
    
    # 关闭时清理
    logger.info("🔄 关闭NEX AI Assistant服务...")
    try:
        if hasattr(app.state, 'orchestrator'):
            await app.state.orchestrator.cleanup()
        if hasattr(app.state, 'plugin_manager'):
            await app.state.plugin_manager.cleanup()
        if hasattr(app.state, 'memory_manager'):
            await app.state.memory_manager.cleanup()
        if hasattr(app.state, 'grpc_client'):
            await app.state.grpc_client.disconnect()
        logger.info("✅ 服务关闭完成")
    except Exception as e:
        logger.error(f"❌ 服务关闭异常: {e}")


# 创建FastAPI应用
app = FastAPI(
    title="NEX AI Assistant",
    description="基于现代化架构的智能助手API服务",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(api_router, prefix="/api/v1", tags=["API"])
app.include_router(websocket_router, prefix="/ws", tags=["WebSocket"])


@app.get("/", tags=["Health"])
async def root():
    """根路径信息"""
    return {
        "name": "NEX AI Assistant",
        "version": "0.1.0",
        "description": "Modern AI Assistant with Plugin Architecture",
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """详细健康检查"""
    try:
        components = {}
        overall_healthy = True
        
        # 检查gRPC连接
        if hasattr(app.state, 'grpc_client'):
            grpc_healthy = await app.state.grpc_client.health_check()
            components["grpc_client"] = "healthy" if grpc_healthy else "unhealthy"
            overall_healthy &= grpc_healthy
        else:
            components["grpc_client"] = "not_initialized"
            overall_healthy = False
        
        # 检查调度器状态
        if hasattr(app.state, 'orchestrator'):
            orchestrator_healthy = app.state.orchestrator.is_healthy()
            components["orchestrator"] = "healthy" if orchestrator_healthy else "unhealthy"
            overall_healthy &= orchestrator_healthy
        else:
            components["orchestrator"] = "not_initialized"
            overall_healthy = False
        
        # 检查记忆管理器
        if hasattr(app.state, 'memory_manager'):
            memory_healthy = await app.state.memory_manager.health_check()
            components["memory_manager"] = "healthy" if memory_healthy else "unhealthy"
            overall_healthy &= memory_healthy
        else:
            components["memory_manager"] = "not_initialized"
        
        # 检查插件管理器  
        if hasattr(app.state, 'plugin_manager'):
            plugin_healthy = app.state.plugin_manager.is_healthy()
            components["plugin_manager"] = "healthy" if plugin_healthy else "unhealthy"
            overall_healthy &= plugin_healthy
        else:
            components["plugin_manager"] = "not_initialized"
        
        return {
            "status": "healthy" if overall_healthy else "unhealthy",
            "timestamp": asyncio.get_event_loop().time(),
            "components": components,
            "architecture": {
                "core_modules": ["inference", "shell", "foundation"],
                "services": ["agent", "memory", "plugin", "gateway"],
                "interfaces": ["cli", "web", "api"]
            }
        }
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        raise HTTPException(status_code=503, detail=f"服务不可用: {str(e)}")


@app.get("/api/v1/system/info", tags=["System"])
async def system_info():
    """系统信息接口"""
    import psutil
    import sys
    
    return {
        "system": {
            "python_version": sys.version,
            "platform": sys.platform,
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total,
            "memory_available": psutil.virtual_memory().available
        },
        "application": {
            "name": "NEX AI Assistant",
            "version": "0.1.0",
            "architecture": "microkernel+plugins",
            "components": {
                "core": ["inference", "shell", "foundation"],
                "services": ["agent", "memory", "plugin", "gateway"],
                "interfaces": ["cli", "web", "api"]
            }
        }
    }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="NEX AI Assistant Server")
    parser.add_argument("--host", default="localhost", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    parser.add_argument("--log-level", default="info", help="Log level")
    
    args = parser.parse_args()
    
    uvicorn.run(
        "main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level
    )