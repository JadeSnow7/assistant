"""
统一API网关 - 整合所有适配器和智能路由
"""
import asyncio
import logging
import time
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import json

from core.adapters import (
    UnifiedChatRequest, UnifiedChatResponse, UnifiedStreamChunk,
    ModelInfo, ProviderType, EngineType
)
from core.model_manager import UnifiedModelManager
from core.gpu_manager import GPUManager
from core.intelligent_router import IntelligentRouter
from core.config_manager import config_manager, get_config


logger = logging.getLogger(__name__)


class UnifiedAPIGateway:
    """统一API网关"""
    
    def __init__(self, grpc_client=None):
        self.grpc_client = grpc_client
        self.model_manager: Optional[UnifiedModelManager] = None
        self.gpu_manager: Optional[GPUManager] = None
        self.router: Optional[IntelligentRouter] = None
        self.app: Optional[FastAPI] = None
        self.initialized = False
        
        # 性能统计
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_latency": 0.0,
            "avg_latency": 0.0,
            "requests_by_provider": {},
            "requests_by_model": {}
        }
    
    async def initialize(self):
        """初始化API网关"""
        try:
            logger.info("初始化统一API网关...")
            
            # 1. 初始化GPU管理器
            self.gpu_manager = GPUManager()
            await self.gpu_manager.initialize()
            
            # 2. 初始化模型管理器
            self.model_manager = UnifiedModelManager(self.grpc_client)
            config = get_config()
            success = await self.model_manager.initialize(config)
            
            if not success:
                logger.warning("模型管理器初始化失败，但继续启动")
            
            # 3. 初始化智能路由器
            self.router = IntelligentRouter(self.model_manager, self.gpu_manager)
            
            # 4. 创建FastAPI应用
            self._create_fastapi_app()
            
            self.initialized = True
            logger.info("统一API网关初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"API网关初始化失败: {e}")
            return False
    
    def _create_fastapi_app(self):
        """创建FastAPI应用"""
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # 启动时的初始化已在外部完成
            yield
            # 关闭时清理资源
            await self.cleanup()
        
        self.app = FastAPI(
            title="统一AI模型API",
            description="支持OpenAI、Gemini、Claude等多种模型的统一API接口",
            version="1.0.0",
            lifespan=lifespan
        )
        
        # 添加CORS中间件
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=get_config("api.cors.origins", ["*"]),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # 注册路由
        self._register_routes()
    
    def _register_routes(self):
        """注册API路由"""
        
        @self.app.post("/v1/chat/completions")
        async def chat_completions(request: UnifiedChatRequest):
            """聊天完成接口 - OpenAI兼容格式"""
            return await self.handle_chat_completion(request)
        
        @self.app.post("/v1/completions")
        async def completions(request: UnifiedChatRequest):
            """文本完成接口"""
            return await self.handle_chat_completion(request)
        
        @self.app.get("/v1/models")
        async def list_models():
            """列出可用模型"""
            return await self.list_available_models()
        
        @self.app.get("/v1/models/{model_id}")
        async def get_model(model_id: str):
            """获取指定模型信息"""
            return await self.get_model_info(model_id)
        
        @self.app.get("/v1/models/{model_id}/health")
        async def check_model_health(model_id: str):
            """检查模型健康状态"""
            return await self.check_model_health(model_id)
        
        @self.app.get("/v1/engines/status")
        async def engines_status():
            """获取引擎状态"""
            return await self.get_engines_status()
        
        @self.app.get("/v1/stats")
        async def get_stats():
            """获取API统计信息"""
            return await self.get_performance_stats()
        
        @self.app.post("/v1/config/update")
        async def update_config_endpoint(path: str, value: Any):
            """更新配置"""
            return await self.update_configuration(path, value)
        
        @self.app.get("/v1/config")
        async def get_config_endpoint(path: str = None):
            """获取配置"""
            return await self.get_configuration(path)
        
        @self.app.get("/v1/health")
        async def health_check():
            """健康检查"""
            return await self.health_check()
    
    async def handle_chat_completion(self, request: UnifiedChatRequest) -> UnifiedChatResponse:
        """处理聊天完成请求"""
        start_time = time.time()
        
        try:
            # 更新统计
            self.stats["total_requests"] += 1
            
            # 智能路由决策
            routing_decision = await self.router.route_request(request)
            
            logger.info(f"路由决策: {routing_decision.provider} -> {routing_decision.model} "
                       f"(置信度: {routing_decision.confidence:.2f}, 原因: {routing_decision.reasoning})")
            
            # 获取适配器
            adapter_manager = self.model_manager.get_adapter_manager()
            adapter = adapter_manager.get_adapter_by_provider(routing_decision.provider)
            
            if not adapter or not adapter.is_healthy():
                # 尝试备选方案
                return await self._handle_fallback(request, routing_decision, start_time)
            
            # 更新请求中的模型信息
            request.model = routing_decision.model
            request.provider = routing_decision.provider
            
            # 执行请求
            if request.stream:
                return await self._handle_stream_request(request, adapter, routing_decision, start_time)
            else:
                response = await adapter.chat_completion(request)
                
                # 更新统计信息
                await self._update_stats(routing_decision, start_time, True)
                
                # 记录性能数据
                latency = (time.time() - start_time) * 1000
                await self.router.record_performance(routing_decision.model, latency, True)
                
                return response
        
        except Exception as e:
            logger.error(f"处理聊天完成请求失败: {e}")
            
            # 更新失败统计
            self.stats["failed_requests"] += 1
            await self._update_stats_on_error(request, start_time)
            
            # 尝试备选方案
            if hasattr(self, 'router') and self.router:
                routing_decision = await self.router.route_request(request)
                return await self._handle_fallback(request, routing_decision, start_time)
            
            # 返回错误响应
            return self._create_error_response(str(e), request)
    
    async def _handle_stream_request(self, request: UnifiedChatRequest, adapter, routing_decision, start_time):
        """处理流式请求"""
        async def generate_stream():
            try:
                full_content = ""
                
                async for chunk in adapter.chat_completion_stream(request):
                    # 统计内容
                    for choice in chunk.choices:
                        delta = choice.get("delta", {})
                        if "content" in delta:
                            full_content += delta["content"]
                    
                    # 转换为SSE格式
                    chunk_data = {
                        "id": chunk.id,
                        "object": chunk.object,
                        "created": chunk.created,
                        "model": chunk.model,
                        "provider": chunk.provider,
                        "choices": chunk.choices
                    }
                    
                    yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
                    
                    # 检查是否结束
                    if any(choice.get("finish_reason") for choice in chunk.choices):
                        break
                
                # 发送结束标记
                yield "data: [DONE]\n\n"
                
                # 更新统计
                await self._update_stats(routing_decision, start_time, True)
                latency = (time.time() - start_time) * 1000
                await self.router.record_performance(routing_decision.model, latency, True)
            
            except Exception as e:
                logger.error(f"流式处理失败: {e}")
                error_chunk = {
                    "id": "error",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": request.model,
                    "choices": [{
                        "index": 0,
                        "delta": {"content": f"错误: {str(e)}"},
                        "finish_reason": "error"
                    }]
                }
                yield f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"
                yield "data: [DONE]\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    
    async def _handle_fallback(self, request: UnifiedChatRequest, failed_decision, start_time):
        """处理备选方案"""
        for fallback_model in failed_decision.fallback_options:
            try:
                logger.info(f"尝试备选模型: {fallback_model}")
                
                # 获取备选模型的适配器
                adapter_manager = self.model_manager.get_adapter_manager()
                adapter = adapter_manager.get_adapter_by_model(fallback_model)
                
                if adapter and adapter.is_healthy():
                    request.model = fallback_model
                    response = await adapter.chat_completion(request)
                    
                    # 记录备选使用
                    await self._update_stats_fallback(fallback_model, start_time)
                    
                    return response
            
            except Exception as e:
                logger.warning(f"备选模型 {fallback_model} 也失败: {e}")
                continue
        
        # 所有备选方案都失败
        return self._create_error_response("所有模型都不可用", request)
    
    async def list_available_models(self) -> Dict[str, Any]:
        """列出可用模型"""
        try:
            models = await self.model_manager.get_available_models()
            
            return {
                "object": "list",
                "data": [
                    {
                        "id": model.id,
                        "object": "model",
                        "provider": model.provider,
                        "engine": model.engine,
                        "capabilities": model.capabilities,
                        "context_length": model.context_length,
                        "status": model.status
                    }
                    for model in models
                ]
            }
        
        except Exception as e:
            logger.error(f"获取模型列表失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_model_info(self, model_id: str) -> Dict[str, Any]:
        """获取指定模型信息"""
        try:
            model = await self.model_manager.get_model_info(model_id)
            
            if not model:
                raise HTTPException(status_code=404, detail=f"模型 {model_id} 未找到")
            
            return {
                "id": model.id,
                "object": "model",
                "provider": model.provider,
                "engine": model.engine,
                "capabilities": model.capabilities,
                "context_length": model.context_length,
                "status": model.status
            }
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"获取模型信息失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def check_model_health(self, model_id: str) -> Dict[str, Any]:
        """检查模型健康状态"""
        try:
            health_data = await self.model_manager.check_model_health(model_id)
            return health_data
        
        except Exception as e:
            logger.error(f"检查模型健康状态失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_engines_status(self) -> Dict[str, Any]:
        """获取引擎状态"""
        try:
            status_dict = await self.model_manager.get_engines_status()
            
            return {
                "engines": {
                    name: {
                        "status": status.status,
                        "provider": status.provider,
                        "models_loaded": status.models_loaded,
                        "memory_usage_mb": status.memory_usage_mb,
                        "gpu_utilization": status.gpu_utilization,
                        "active_sessions": status.active_sessions,
                        "last_check": status.last_check,
                        "error": status.error
                    }
                    for name, status in status_dict.items()
                }
            }
        
        except Exception as e:
            logger.error(f"获取引擎状态失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        try:
            # 合并API网关统计和路由器统计
            router_stats = self.router.get_performance_stats() if self.router else {}
            
            return {
                "api_gateway": self.stats,
                "router_performance": router_stats,
                "gpu_info": await self.gpu_manager.get_gpu_info() if self.gpu_manager else []
            }
        
        except Exception as e:
            logger.error(f"获取性能统计失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def update_configuration(self, path: str, value: Any) -> Dict[str, str]:
        """更新配置"""
        try:
            from core.config_manager import update_config
            await update_config(path, value)
            
            return {"message": f"配置 {path} 已更新为 {value}"}
        
        except Exception as e:
            logger.error(f"更新配置失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_configuration(self, path: str = None) -> Dict[str, Any]:
        """获取配置"""
        try:
            from core.config_manager import get_config
            
            if path:
                value = get_config(path)
                return {"path": path, "value": value}
            else:
                config = get_config()
                return config
        
        except Exception as e:
            logger.error(f"获取配置失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            health_status = {
                "status": "healthy" if self.initialized else "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "components": {
                    "model_manager": self.model_manager is not None,
                    "gpu_manager": self.gpu_manager is not None and self.gpu_manager.initialized,
                    "router": self.router is not None,
                    "config_manager": config_manager.initialized if hasattr(config_manager, 'initialized') else True
                }
            }
            
            # 检查适配器健康状态
            if self.model_manager:
                adapter_health = await self.model_manager.get_adapter_manager().health_check_all()
                health_status["adapters"] = adapter_health
            
            return health_status
        
        except Exception as e:
            logger.error(f"健康检查失败: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _update_stats(self, routing_decision, start_time: float, success: bool):
        """更新统计信息"""
        latency = (time.time() - start_time) * 1000
        
        if success:
            self.stats["successful_requests"] += 1
        
        # 更新平均延迟
        total_successful = self.stats["successful_requests"]
        if total_successful > 0:
            self.stats["total_latency"] += latency
            self.stats["avg_latency"] = self.stats["total_latency"] / total_successful
        
        # 按provider统计
        provider = routing_decision.provider
        if provider not in self.stats["requests_by_provider"]:
            self.stats["requests_by_provider"][provider] = 0
        self.stats["requests_by_provider"][provider] += 1
        
        # 按model统计
        model = routing_decision.model
        if model not in self.stats["requests_by_model"]:
            self.stats["requests_by_model"][model] = 0
        self.stats["requests_by_model"][model] += 1
    
    async def _update_stats_on_error(self, request, start_time: float):
        """更新错误统计"""
        latency = (time.time() - start_time) * 1000
        
        # 记录失败的请求
        if "errors" not in self.stats:
            self.stats["errors"] = []
        
        self.stats["errors"].append({
            "timestamp": datetime.now().isoformat(),
            "latency_ms": latency,
            "request_model": request.model,
            "request_provider": request.provider
        })
        
        # 只保留最近100个错误
        if len(self.stats["errors"]) > 100:
            self.stats["errors"] = self.stats["errors"][-100:]
    
    async def _update_stats_fallback(self, fallback_model: str, start_time: float):
        """更新备选方案统计"""
        if "fallbacks" not in self.stats:
            self.stats["fallbacks"] = {}
        
        if fallback_model not in self.stats["fallbacks"]:
            self.stats["fallbacks"][fallback_model] = 0
        
        self.stats["fallbacks"][fallback_model] += 1
    
    def _create_error_response(self, error_msg: str, request: UnifiedChatRequest) -> UnifiedChatResponse:
        """创建错误响应"""
        return UnifiedChatResponse(
            id="error-" + str(int(time.time())),
            model=request.model or "unknown",
            provider="gateway",
            engine="unknown",
            choices=[{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": f"抱歉，处理您的请求时出现错误：{error_msg}"
                },
                "finish_reason": "error"
            }],
            usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        )
    
    def get_app(self) -> FastAPI:
        """获取FastAPI应用实例"""
        return self.app
    
    async def cleanup(self):
        """清理资源"""
        try:
            if self.model_manager:
                await self.model_manager.cleanup()
            
            logger.info("API网关资源已清理")
        
        except Exception as e:
            logger.error(f"清理API网关资源失败: {e}")


# 创建全局网关实例
gateway = UnifiedAPIGateway()


async def create_app(grpc_client=None) -> FastAPI:
    """创建并初始化应用"""
    global gateway
    
    # 初始化配置管理器
    from core.config_manager import initialize_config_manager
    await initialize_config_manager()
    
    # 设置gRPC客户端
    gateway.grpc_client = grpc_client
    
    # 初始化网关
    success = await gateway.initialize()
    
    if not success:
        logger.warning("API网关初始化失败，但继续启动")
    
    return gateway.get_app()


if __name__ == "__main__":
    import uvicorn
    import json
    
    async def main():
        app = await create_app()
        
        # 获取配置
        api_config = get_config("api")
        host = api_config.get("host", "0.0.0.0")
        port = api_config.get("port", 8000)
        
        # 启动服务器
        config = uvicorn.Config(
            app,
            host=host,
            port=port,
            log_level="info"
        )
        
        server = uvicorn.Server(config)
        await server.serve()
    
    asyncio.run(main())