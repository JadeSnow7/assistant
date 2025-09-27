"""
AI Assistant - Python应用层入口
"""
import asyncio
import logging
import uvicorn
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from agent.orchestrator import AgentOrchestrator
from agent.api_router import api_router
from agent.websocket_handler import websocket_router
from core.config import settings
from core.grpc_client import GRPCClient


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
    logger.info("启动AI Assistant服务...")
    
    # 初始化gRPC客户端
    grpc_client = GRPCClient(settings.grpc_server_address)
    await grpc_client.connect()
    app.state.grpc_client = grpc_client
    
    # 初始化Agent调度器
    orchestrator = AgentOrchestrator(grpc_client)
    await orchestrator.initialize()
    app.state.orchestrator = orchestrator
    
    logger.info("服务启动完成")
    
    yield
    
    # 关闭时清理
    logger.info("关闭AI Assistant服务...")
    await orchestrator.cleanup()
    await grpc_client.disconnect()
    logger.info("服务关闭完成")


# 创建FastAPI应用
app = FastAPI(
    title="AI Assistant",
    description="智能助手API服务",
    version="1.0.0",
    lifespan=lifespan
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
app.include_router(api_router, prefix="/api/v1")
app.include_router(websocket_router, prefix="/ws")


@app.get("/")
async def root():
    """根路径健康检查"""
    return {
        "message": "AI Assistant API服务运行中",
        "version": "1.0.0",
        "status": "healthy"
    }


@app.get("/health")
async def health_check():
    """详细健康检查"""
    try:
        grpc_client = app.state.grpc_client
        orchestrator = app.state.orchestrator
        
        # 检查gRPC连接
        grpc_healthy = await grpc_client.health_check()
        
        # 检查调度器状态
        orchestrator_healthy = orchestrator.is_healthy()
        
        return {
            "status": "healthy" if grpc_healthy and orchestrator_healthy else "unhealthy",
            "components": {
                "grpc_client": "healthy" if grpc_healthy else "unhealthy",
                "orchestrator": "healthy" if orchestrator_healthy else "unhealthy"
            }
        }
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        raise HTTPException(status_code=503, detail="服务不可用")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info"
    )