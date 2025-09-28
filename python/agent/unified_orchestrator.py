"""
统一Agent调度器 - 使用新的统一API系统
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any, AsyncGenerator
from datetime import datetime

from core.unified_api_gateway import UnifiedAPIGateway
from core.adapters import UnifiedChatRequest, UnifiedChatResponse
from core.memory_manager import MemoryManager
from core.plugin_manager import PluginManager
from models.schemas import (
    ChatRequest, ChatResponse, TaskRequest, TaskResponse,
    ModelType, TaskStatus
)


logger = logging.getLogger(__name__)


class UnifiedOrchestrator:
    """统一Agent调度器 - 使用新的API系统"""
    
    def __init__(self, grpc_client=None):
        self.gateway = UnifiedAPIGateway(grpc_client)
        self.memory_manager = MemoryManager()
        self.plugin_manager = PluginManager()
        
        # 任务队列
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.active_tasks: Dict[str, TaskStatus] = {}
        
        # 性能统计
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "avg_response_time": 0.0,
            "plugin_calls": 0,
            "memory_operations": 0
        }
    
    async def initialize(self):
        """初始化统一调度器"""
        logger.info("初始化统一Agent调度器...")
        
        try:
            # 初始化网关
            await self.gateway.initialize()
            
            # 初始化其他组件
            await self.memory_manager.initialize()
            await self.plugin_manager.initialize()
            
            # 启动任务处理器
            asyncio.create_task(self._task_processor())
            
            logger.info("统一Agent调度器初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"统一调度器初始化失败: {e}")
            return False
    
    async def process_chat(self, request: ChatRequest) -> ChatResponse:
        """处理聊天请求"""
        start_time = datetime.now()
        session_id = request.session_id or f"session_{start_time.timestamp()}"
        
        try:
            self.stats["total_requests"] += 1
            
            # 1. 加载会话记忆
            context = await self.memory_manager.get_session_context(session_id)
            
            # 2. 检查是否需要插件处理
            plugin_result = await self._check_plugin_requirements(request.message, context)
            if plugin_result:
                return await self._handle_plugin_response(plugin_result, request, session_id, start_time)
            
            # 3. 转换为统一API请求格式
            unified_request = self._convert_to_unified_request(request, context)
            
            # 4. 调用统一API网关
            unified_response = await self.gateway.handle_chat_completion(unified_request)
            
            # 5. 转换回原始格式
            response = self._convert_from_unified_response(unified_response, request, session_id)
            
            # 6. 更新记忆
            await self.memory_manager.update_session(
                session_id, request.message, response.content
            )
            self.stats["memory_operations"] += 1
            
            # 7. 更新统计
            self._update_stats(start_time, True)
            
            return response
            
        except Exception as e:
            logger.error(f"处理聊天请求失败: {e}")
            self._update_stats(start_time, False)
            
            return ChatResponse(
                content="抱歉，处理您的请求时出现了错误，请稍后重试。",
                session_id=session_id,
                model_used=ModelType.LOCAL_SMALL,
                error=str(e),
                timestamp=datetime.now()
            )
    
    async def process_chat_stream(self, request: ChatRequest) -> AsyncGenerator[ChatResponse, None]:
        """流式处理聊天请求"""
        start_time = datetime.now()
        session_id = request.session_id or f"session_{start_time.timestamp()}"
        
        try:
            # 加载会话记忆
            context = await self.memory_manager.get_session_context(session_id)
            
            # 检查插件需求
            plugin_result = await self._check_plugin_requirements(request.message, context)
            if plugin_result:
                # 插件响应（非流式）
                response = await self._handle_plugin_response(plugin_result, request, session_id, start_time)
                yield response
                return
            
            # 转换为统一API请求
            unified_request = self._convert_to_unified_request(request, context)
            unified_request.stream = True
            
            # 调用统一API网关的流式处理
            full_content = ""
            async for chunk_response in self._process_unified_stream(unified_request):
                if chunk_response.content:
                    full_content += chunk_response.content
                
                # 转换为ChatResponse格式
                response = ChatResponse(
                    content=chunk_response.content,
                    session_id=session_id,
                    model_used=self._convert_model_type(chunk_response.model_used),
                    reasoning=chunk_response.reasoning,
                    token_count=chunk_response.token_count,
                    latency_ms=chunk_response.latency_ms,
                    confidence=chunk_response.confidence,
                    timestamp=datetime.now()
                )
                
                yield response
            
            # 更新记忆（使用完整内容）
            if full_content:
                await self.memory_manager.update_session(
                    session_id, request.message, full_content
                )
                self.stats["memory_operations"] += 1
            
            self._update_stats(start_time, True)
            
        except Exception as e:
            logger.error(f"流式聊天处理失败: {e}")
            self._update_stats(start_time, False)
            
            yield ChatResponse(
                content=f"抱歉，处理您的请求时出现了错误：{str(e)}",
                session_id=session_id,
                model_used=ModelType.LOCAL_SMALL,
                error=str(e),
                timestamp=datetime.now()
            )
    
    async def _process_unified_stream(self, request: UnifiedChatRequest) -> AsyncGenerator[ChatResponse, None]:
        """处理统一API的流式响应"""
        # 这里需要实现从网关获取流式响应的逻辑
        # 由于网关的流式处理返回StreamingResponse，我们需要解析
        
        # 临时实现：调用非流式接口并模拟流式输出
        response = await self.gateway.handle_chat_completion(request)
        
        # 模拟流式输出
        content = response.choices[0]["message"]["content"] if response.choices else ""
        words = content.split()
        
        accumulated_content = ""
        for word in words:
            accumulated_content += word + " "
            
            yield ChatResponse(
                content=word + " ",
                session_id=request.session_id,
                model_used=self._map_provider_to_model_type(response.provider),
                reasoning=f"使用 {response.provider} 模型",
                timestamp=datetime.now()
            )
            
            await asyncio.sleep(0.05)  # 模拟打字效果
    
    async def _check_plugin_requirements(self, message: str, context: Dict) -> Optional[Dict[str, Any]]:
        """检查是否需要插件处理"""
        # 简单的插件匹配逻辑
        message_lower = message.lower()
        
        plugin_keywords = {
            "weather": ["天气", "温度", "下雨", "weather", "temperature"],
            "calendar": ["日程", "日历", "会议", "calendar", "schedule"],
            "file": ["文件", "保存", "读取", "file", "save", "read"]
        }
        
        for plugin_name, keywords in plugin_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                # 检查插件是否可用
                available_plugins = await self.plugin_manager.get_available_plugins()
                if plugin_name in available_plugins:
                    return {
                        "plugin_name": plugin_name,
                        "command": "process",
                        "parameters": {"message": message, "context": context}
                    }
        
        return None
    
    async def _handle_plugin_response(self, plugin_info: Dict[str, Any], request: ChatRequest, session_id: str, start_time: datetime) -> ChatResponse:
        """处理插件响应"""
        try:
            self.stats["plugin_calls"] += 1
            
            result = await self.plugin_manager.execute_plugin(
                plugin_info["plugin_name"],
                plugin_info["command"],
                plugin_info["parameters"]
            )
            
            content = result.get("result", "插件执行完成") if result.get("success") else f"插件执行失败: {result.get('error')}"
            
            return ChatResponse(
                content=content,
                session_id=session_id,
                model_used=ModelType.PLUGIN,
                reasoning=f"使用 {plugin_info['plugin_name']} 插件处理",
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"插件处理失败: {e}")
            return ChatResponse(
                content=f"插件处理失败: {str(e)}",
                session_id=session_id,
                model_used=ModelType.PLUGIN,
                error=str(e),
                timestamp=datetime.now()
            )
    
    def _convert_to_unified_request(self, request: ChatRequest, context: Dict) -> UnifiedChatRequest:
        """转换为统一API请求格式"""
        # 构建消息列表
        messages = []
        
        # 添加系统消息（如果有上下文）
        if context.get("system_prompt"):
            messages.append({
                "role": "system",
                "content": context["system_prompt"]
            })
        
        # 添加历史消息（最近几条）
        recent_messages = context.get("recent_messages", [])[-5:]  # 最近5条
        for msg in recent_messages:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })
        
        # 添加当前用户消息
        messages.append({
            "role": "user",
            "content": request.message
        })
        
        # 转换模型选择
        model = request.preferred_model
        provider = "auto"
        
        if request.model_type:
            if request.model_type == ModelType.LOCAL_SMALL:
                provider = "llamacpp"
                model = model or "qwen3:4b"
            elif request.model_type == ModelType.CLOUD_LARGE:
                provider = "gemini"
                model = model or "gemini-1.5-pro"
        
        return UnifiedChatRequest(
            model=model or "auto",
            messages=messages,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            stream=request.stream,
            session_id=request.session_id,
            provider=provider
        )
    
    def _convert_from_unified_response(self, response: UnifiedChatResponse, request: ChatRequest, session_id: str) -> ChatResponse:
        """转换统一API响应为ChatResponse"""
        content = ""
        if response.choices:
            choice = response.choices[0]
            message = choice.get("message", {})
            content = message.get("content", "")
        
        # 计算模型类型
        model_used = self._map_provider_to_model_type(response.provider)
        
        # 推理说明
        reasoning = f"使用 {response.provider} 的 {response.model} 模型"
        if response.performance:
            reasoning += f"，延迟 {response.performance.get('latency_ms', 0):.0f}ms"
        
        return ChatResponse(
            content=content,
            session_id=session_id,
            model_used=model_used,
            reasoning=reasoning,
            token_count=response.usage.get("total_tokens") if response.usage else None,
            latency_ms=response.performance.get("latency_ms") if response.performance else None,
            confidence=0.9,  # 默认置信度
            timestamp=datetime.now()
        )
    
    def _map_provider_to_model_type(self, provider: str) -> ModelType:
        """映射provider到ModelType"""
        mapping = {
            "llamacpp": ModelType.LOCAL_SMALL,
            "ollama": ModelType.LOCAL_SMALL,
            "openai": ModelType.CLOUD_LARGE,
            "gemini": ModelType.CLOUD_LARGE,
            "claude": ModelType.CLOUD_LARGE
        }
        return mapping.get(provider, ModelType.AUTO_SELECT)
    
    def _convert_model_type(self, model_type_str: str) -> ModelType:
        """转换模型类型字符串"""
        # 这个函数处理从unified response来的model_used字段
        if hasattr(ModelType, model_type_str.upper()):
            return getattr(ModelType, model_type_str.upper())
        return ModelType.AUTO_SELECT
    
    async def create_background_task(self, request: TaskRequest) -> str:
        """创建后台任务"""
        import uuid
        task_id = str(uuid.uuid4())
        
        # 将任务添加到队列
        await self.task_queue.put({
            "task_id": task_id,
            "request": request,
            "created_at": datetime.now()
        })
        
        # 记录任务状态
        self.active_tasks[task_id] = TaskStatus.CREATED
        
        return task_id
    
    async def get_task_status(self, task_id: str) -> Optional[TaskResponse]:
        """获取任务状态"""
        if task_id not in self.active_tasks:
            return None
        
        status = self.active_tasks[task_id]
        
        return TaskResponse(
            task_id=task_id,
            status=status,
            progress=0.5 if status == TaskStatus.RUNNING else (1.0 if status == TaskStatus.COMPLETED else 0.0),
            message=f"任务状态: {status.value}"
        )
    
    async def _task_processor(self):
        """任务队列处理器"""
        while True:
            try:
                if not self.task_queue.empty():
                    task = await self.task_queue.get()
                    await self._process_background_task(task)
                else:
                    await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"任务处理器错误: {e}")
                await asyncio.sleep(1)
    
    async def _process_background_task(self, task: Dict[str, Any]):
        """处理后台任务"""
        task_id = task["task_id"]
        
        try:
            self.active_tasks[task_id] = TaskStatus.RUNNING
            
            # 这里实现具体的任务处理逻辑
            await asyncio.sleep(2)  # 模拟任务处理
            
            self.active_tasks[task_id] = TaskStatus.COMPLETED
            
        except Exception as e:
            logger.error(f"后台任务处理失败 {task_id}: {e}")
            self.active_tasks[task_id] = TaskStatus.FAILED
    
    def _update_stats(self, start_time: datetime, success: bool):
        """更新性能统计"""
        if success:
            self.stats["successful_requests"] += 1
        else:
            self.stats["failed_requests"] += 1
        
        # 计算响应时间
        response_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # 更新平均响应时间
        total_successful = self.stats["successful_requests"]
        if total_successful > 0:
            self.stats["avg_response_time"] = (
                self.stats["avg_response_time"] * (total_successful - 1) + response_time
            ) / total_successful
    
    def get_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        # 合并本地统计和网关统计
        gateway_stats = {}
        if hasattr(self.gateway, 'stats'):
            gateway_stats = self.gateway.stats
        
        return {
            "orchestrator": self.stats,
            "gateway": gateway_stats,
            "components": {
                "memory_manager": self.memory_manager.is_healthy() if hasattr(self.memory_manager, 'is_healthy') else True,
                "plugin_manager": self.plugin_manager.is_healthy() if hasattr(self.plugin_manager, 'is_healthy') else True,
                "gateway": self.gateway.initialized
            }
        }
    
    def is_healthy(self) -> bool:
        """健康检查"""
        return (
            self.gateway.initialized and
            (not hasattr(self.memory_manager, 'is_healthy') or self.memory_manager.is_healthy()) and
            (not hasattr(self.plugin_manager, 'is_healthy') or self.plugin_manager.is_healthy())
        )
    
    async def cleanup(self):
        """清理资源"""
        logger.info("清理统一Agent调度器资源...")
        
        try:
            await self.gateway.cleanup()
            await self.memory_manager.cleanup()
            await self.plugin_manager.cleanup()
        except Exception as e:
            logger.error(f"清理资源失败: {e}")
        
        logger.info("资源清理完成")