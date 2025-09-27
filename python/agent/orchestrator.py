"""
Agent调度器 - 智能任务编排核心
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

from core.grpc_client import GRPCClient
from core.memory_manager import MemoryManager
from core.plugin_manager import PluginManager
from core.cloud_client import CloudClient
from models.schemas import (
    ChatRequest, ChatResponse, TaskRequest, TaskResponse,
    ModelType, TaskStatus
)


logger = logging.getLogger(__name__)


class DecisionStrategy(Enum):
    """决策策略枚举"""
    LOCAL_FIRST = "local_first"          # 优先本地
    CLOUD_FIRST = "cloud_first"          # 优先云端
    SMART_ROUTE = "smart_route"          # 智能路由
    LOAD_BALANCE = "load_balance"        # 负载均衡


class AgentOrchestrator:
    """智能Agent调度器"""
    
    def __init__(self, grpc_client: GRPCClient):
        self.grpc_client = grpc_client
        self.memory_manager = MemoryManager()
        self.plugin_manager = PluginManager()
        self.cloud_client = CloudClient()
        
        # 决策引擎配置
        self.decision_strategy = DecisionStrategy.SMART_ROUTE
        self.local_model_threshold = 0.8  # 本地模型置信度阈值
        self.max_tokens_local = 2048       # 本地模型最大token数
        
        # 任务队列
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.active_tasks: Dict[str, TaskStatus] = {}
        
        # 性能统计
        self.stats = {
            "total_requests": 0,
            "local_requests": 0,
            "cloud_requests": 0,
            "plugin_requests": 0,
            "avg_response_time": 0.0,
        }
    
    async def initialize(self):
        """初始化调度器"""
        logger.info("初始化Agent调度器...")
        
        # 初始化各组件
        await self.memory_manager.initialize()
        await self.plugin_manager.initialize()
        await self.cloud_client.initialize()
        
        # 启动任务处理器
        asyncio.create_task(self._task_processor())
        
        logger.info("Agent调度器初始化完成")
    
    async def process_chat(self, request: ChatRequest) -> ChatResponse:
        """处理聊天请求"""
        start_time = datetime.now()
        session_id = request.session_id or f"session_{start_time.timestamp()}"
        
        try:
            # 1. 加载会话记忆
            context = await self.memory_manager.get_session_context(session_id)
            
            # 2. 分析用户意图
            intent = await self._analyze_intent(request.message, context)
            
            # 3. 决策执行策略
            strategy = await self._decide_strategy(request, intent, context)
            
            # 4. 执行任务
            response = await self._execute_strategy(strategy, request, intent, context)
            
            # 5. 更新记忆
            await self.memory_manager.update_session(
                session_id, request.message, response.content
            )
            
            # 6. 更新统计
            self._update_stats(strategy, start_time)
            
            return response
            
        except Exception as e:
            logger.error(f"处理聊天请求失败: {e}")
            return ChatResponse(
                content="抱歉，处理您的请求时出现了错误，请稍后重试。",
                session_id=session_id,
                model_used=ModelType.LOCAL_SMALL,
                error=str(e)
            )
    
    async def _analyze_intent(self, message: str, context: Dict) -> Dict[str, Any]:
        """分析用户意图"""
        # 使用本地小模型进行意图分析
        intent_prompt = f"""
        分析以下用户消息的意图，返回JSON格式：
        消息: {message}
        上下文: {context.get('recent_messages', [])}
        
        返回格式:
        {{
            "intent_type": "chat|search|plugin|system",
            "confidence": 0.0-1.0,
            "entities": [],
            "requires_web": true/false,
            "complexity": "simple|medium|complex"
        }}
        """
        
        # 调用本地模型
        response = await self.grpc_client.inference(
            prompt=intent_prompt,
            model_type="intent_analyzer",
            max_tokens=256
        )
        
        try:
            import json
            intent = json.loads(response.text)
            return intent
        except:
            # 解析失败时返回默认意图
            return {
                "intent_type": "chat",
                "confidence": 0.5,
                "entities": [],
                "requires_web": False,
                "complexity": "medium"
            }
    
    async def _decide_strategy(
        self, 
        request: ChatRequest, 
        intent: Dict[str, Any], 
        context: Dict
    ) -> Dict[str, Any]:
        """决策执行策略"""
        
        strategy = {
            "use_local": False,
            "use_cloud": False,
            "use_plugin": False,
            "plugin_name": None,
            "model_type": ModelType.AUTO_SELECT,
            "reasoning": ""
        }
        
        # 根据意图类型决策
        if intent["intent_type"] == "plugin":
            # 需要插件处理
            plugin_name = await self._find_suitable_plugin(intent["entities"])
            if plugin_name:
                strategy.update({
                    "use_plugin": True,
                    "plugin_name": plugin_name,
                    "reasoning": f"使用{plugin_name}插件处理特定功能"
                })
                return strategy
        
        # 检查是否需要联网搜索
        if intent.get("requires_web", False):
            strategy.update({
                "use_cloud": True,
                "model_type": ModelType.CLOUD_LARGE,
                "reasoning": "需要最新信息，使用云端模型"
            })
            return strategy
        
        # 根据复杂度和当前系统资源决策
        system_info = await self.grpc_client.get_system_info()
        
        if intent["complexity"] == "simple" and system_info.memory_usage < 70:
            # 简单任务且资源充足，使用本地模型
            strategy.update({
                "use_local": True,
                "model_type": ModelType.LOCAL_SMALL,
                "reasoning": "简单任务，本地模型处理"
            })
        elif intent["complexity"] == "complex" or len(request.message) > 1000:
            # 复杂任务使用云端大模型
            strategy.update({
                "use_cloud": True,
                "model_type": ModelType.CLOUD_LARGE,
                "reasoning": "复杂任务，使用云端大模型"
            })
        else:
            # 中等复杂度，智能选择
            if intent["confidence"] > self.local_model_threshold:
                strategy.update({
                    "use_local": True,
                    "model_type": ModelType.LOCAL_SMALL,
                    "reasoning": "高置信度任务，本地模型处理"
                })
            else:
                strategy.update({
                    "use_cloud": True,
                    "model_type": ModelType.CLOUD_LARGE,
                    "reasoning": "低置信度任务，云端模型处理"
                })
        
        return strategy
    
    async def _execute_strategy(
        self,
        strategy: Dict[str, Any],
        request: ChatRequest,
        intent: Dict[str, Any],
        context: Dict
    ) -> ChatResponse:
        """执行决策策略"""
        
        if strategy["use_plugin"]:
            # 使用插件处理
            result = await self.plugin_manager.execute_plugin(
                strategy["plugin_name"],
                request.message,
                context
            )
            return ChatResponse(
                content=result,
                session_id=request.session_id,
                model_used=ModelType.PLUGIN,
                reasoning=strategy["reasoning"]
            )
        
        elif strategy["use_local"]:
            # 使用本地模型
            response = await self.grpc_client.inference(
                prompt=request.message,
                model_type="chat",
                max_tokens=request.max_tokens or 1024,
                temperature=request.temperature or 0.7
            )
            return ChatResponse(
                content=response.text,
                session_id=request.session_id,
                model_used=ModelType.LOCAL_SMALL,
                reasoning=strategy["reasoning"],
                token_count=response.token_count,
                latency_ms=response.latency_ms
            )
        
        elif strategy["use_cloud"]:
            # 使用云端模型
            response = await self.cloud_client.chat_completion(
                messages=[{"role": "user", "content": request.message}],
                model=request.preferred_model or "gpt-4",
                max_tokens=request.max_tokens or 2048,
                temperature=request.temperature or 0.7
            )
            return ChatResponse(
                content=response["content"],
                session_id=request.session_id,
                model_used=ModelType.CLOUD_LARGE,
                reasoning=strategy["reasoning"],
                token_count=response.get("token_count", 0)
            )
    
    async def _find_suitable_plugin(self, entities: List[str]) -> Optional[str]:
        """根据实体找到合适的插件"""
        available_plugins = await self.plugin_manager.get_available_plugins()
        
        # 简单的插件匹配逻辑
        entity_plugin_map = {
            "weather": "weather_plugin",
            "music": "music_plugin",
            "calendar": "calendar_plugin",
            "email": "email_plugin",
            "file": "file_manager_plugin"
        }
        
        for entity in entities:
            entity_lower = entity.lower()
            for keyword, plugin_name in entity_plugin_map.items():
                if keyword in entity_lower and plugin_name in available_plugins:
                    return plugin_name
        
        return None
    
    async def _task_processor(self):
        """任务队列处理器"""
        while True:
            try:
                # 处理队列中的任务
                if not self.task_queue.empty():
                    task = await self.task_queue.get()
                    await self._process_background_task(task)
                else:
                    await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"任务处理器错误: {e}")
                await asyncio.sleep(1)
    
    async def _process_background_task(self, task: TaskRequest):
        """处理后台任务"""
        # 实现后台任务处理逻辑
        pass
    
    def _update_stats(self, strategy: Dict[str, Any], start_time: datetime):
        """更新性能统计"""
        self.stats["total_requests"] += 1
        
        if strategy["use_local"]:
            self.stats["local_requests"] += 1
        elif strategy["use_cloud"]:
            self.stats["cloud_requests"] += 1
        elif strategy["use_plugin"]:
            self.stats["plugin_requests"] += 1
        
        # 计算响应时间
        response_time = (datetime.now() - start_time).total_seconds() * 1000
        self.stats["avg_response_time"] = (
            self.stats["avg_response_time"] * (self.stats["total_requests"] - 1) + response_time
        ) / self.stats["total_requests"]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        return self.stats.copy()
    
    def is_healthy(self) -> bool:
        """健康检查"""
        return (
            self.memory_manager.is_healthy() and
            self.plugin_manager.is_healthy() and
            self.cloud_client.is_healthy()
        )
    
    async def cleanup(self):
        """清理资源"""
        logger.info("清理Agent调度器资源...")
        await self.memory_manager.cleanup()
        await self.plugin_manager.cleanup()
        await self.cloud_client.cleanup()
        logger.info("资源清理完成")