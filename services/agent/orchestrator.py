"""
Agent调度器 - 智能任务编排核心
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

from core.foundation.grpc_client import GRPCClient
from core.foundation.memory_manager import MemoryManager
from core.foundation.plugin_manager import PluginManager
from core.foundation.cloud_client import CloudClient
from interfaces.api.schemas import (
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
            response = await self._execute_strategy(strategy, request, intent, context, session_id)
            
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
你是一个智能助手，需要分析用户意图。请以JSON格式返回分析结果。

用户消息: {message}
上下文: {context.get('recent_messages', [])[-3:] if context.get('recent_messages') else []}

请分析以下几个方面:
1. intent_type: 意图类型 (chat|日常对话, search|搜索查询, plugin|特定功能, system|系统命令)
2. confidence: 置信度 (0.0-1.0)
3. entities: 关键实体列表 
4. requires_web: 是否需要联网搜索 (true/false)
5. complexity: 复杂度 (simple|简单, medium|中等, complex|复杂)

请只返回JSON，不要其他文本。
        """
        
        try:
            # 调用本地模型进行意图分析
            response = await self.grpc_client.inference(
                prompt=intent_prompt,
                model_type="intent_analyzer",
                max_tokens=256,
                temperature=0.3  # 使用较低的温度保证结果一致性
            )
            
            # 尝试解析JSON结果
            import json
            response_text = response["text"].strip()
            
            # 尝试从响应中提取JSON
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                intent = json.loads(json_str)
                
                # 验证必需字段
                required_fields = ["intent_type", "confidence", "complexity"]
                for field in required_fields:
                    if field not in intent:
                        raise ValueError(f"缺少必需字段: {field}")
                
                # 设置默认值
                intent.setdefault("entities", [])
                intent.setdefault("requires_web", False)
                
                logger.info(f"意图分析结果: {intent}")
                return intent
                
        except Exception as e:
            logger.warning(f"意图分析失败: {e}，使用默认分析")
        
        # 如果分析失败，使用简单的规则分析
        return self._simple_intent_analysis(message)
    
    def _simple_intent_analysis(self, message: str) -> Dict[str, Any]:
        """简单的规则意图分析"""
        message_lower = message.lower()
        
        # 检测是否需要联网搜索
        web_keywords = ["最新", "今天", "现在", "新闻", "天气", "股价", "汇率"]
        requires_web = any(keyword in message for keyword in web_keywords)
        
        # 检测插件功能
        plugin_keywords = {
            "weather": ["天气", "温度", "下雨"],
            "music": ["音乐", "歌曲", "播放"],
            "file": ["文件", "保存", "读取"]
        }
        
        entities = []
        intent_type = "chat"
        
        for plugin, keywords in plugin_keywords.items():
            for keyword in keywords:
                if keyword in message:
                    intent_type = "plugin"
                    entities.append(plugin)
                    break
        
        if requires_web and intent_type == "chat":
            intent_type = "search"
        
        # 检测复杂度
        complexity = "simple"
        if len(message) > 100:
            complexity = "medium"
        if len(message) > 300 or "请详细" in message or "分析" in message:
            complexity = "complex"
        
        return {
            "intent_type": intent_type,
            "confidence": 0.7,
            "entities": entities,
            "requires_web": requires_web,
            "complexity": complexity
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
        
        # 简单任务的关键词
        simple_keywords = ["你好", "谢谢", "再见", "问好", "是吗", "对吗"]
        
        # 中等复杂度的关键词
        medium_keywords = ["什么是", "如何", "怎么", "为什么", "可以吗"]
        
        # 复杂任务的关键词
        complex_keywords = [
            "请详细", "分析", "解释", "设计", "制定", "规划", 
            "代码", "程序", "算法", "架构", "系统", "方案",
            "写一个", "帮我写", "创建", "开发", "实现", "教程"
        ]
        
        message_lower = request.message.lower()
        
        # 检测简单任务
        if (any(keyword in request.message for keyword in simple_keywords) or 
            len(request.message) < 20):
            strategy.update({
                "use_local": True,
                "model_type": ModelType.LOCAL_SMALL,
                "reasoning": "简单任务，本地模型处理"
            })
        # 检测复杂任务
        elif (any(keyword in request.message for keyword in complex_keywords) or 
              len(request.message) > 200 or 
              intent["complexity"] == "complex"):
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
    
    async def process_chat_stream(self, request: ChatRequest):
        """流式处理聊天请求"""
        start_time = datetime.now()
        session_id = request.session_id or f"session_{start_time.timestamp()}"
        
        try:
            # 1. 加载会话记忆
            context = await self.memory_manager.get_session_context(session_id)
            
            # 2. 分析用户意图
            intent = await self._analyze_intent(request.message, context)
            
            # 3. 决策执行策略
            strategy = await self._decide_strategy(request, intent, context)
            
            # 4. 流式执行任务
            full_response = ""
            
            if strategy["use_cloud"]:
                # 使用云端流式API
                async for chunk in self.cloud_client.chat_completion_stream(
                    messages=[{"role": "user", "content": request.message}],
                    model=request.preferred_model or "gpt-3.5-turbo",
                    max_tokens=request.max_tokens or 1024,
                    temperature=request.temperature or 0.7
                ):
                    if "content" in chunk:
                        full_response += chunk["content"]
                        yield ChatResponse(
                            content=chunk["content"],
                            session_id=session_id,
                            model_used=ModelType.CLOUD_LARGE,
                            reasoning=strategy["reasoning"]
                        )
                    
                    if chunk.get("finished", False):
                        break
            else:
                # 非流式处理，转换为流式输出
                response = await self._execute_strategy(strategy, request, intent, context, session_id)
                
                # 模拟流式输出
                words = response.content.split()
                for i, word in enumerate(words):
                    yield ChatResponse(
                        content=word + " ",
                        session_id=session_id,
                        model_used=response.model_used,
                        reasoning=response.reasoning
                    )
                    await asyncio.sleep(0.05)  # 模拟打字效果
                
                full_response = response.content
            
            # 5. 更新记忆
            await self.memory_manager.update_session(
                session_id, request.message, full_response
            )
            
            # 6. 更新统计
            self._update_stats(strategy, start_time)
            
        except Exception as e:
            logger.error(f"流式聊天处理失败: {e}")
            yield ChatResponse(
                content="抱歉，处理您的请求时出现了错误。",
                session_id=session_id,
                model_used=ModelType.LOCAL_SMALL,
                error=str(e)
            )
    
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
    
    async def _execute_strategy(
        self,
        strategy: Dict[str, Any],
        request: ChatRequest,
        intent: Dict[str, Any],
        context: Dict,
        session_id: str
    ) -> ChatResponse:
        """执行决策策略"""
        
        if strategy["use_plugin"]:
            # 使用插件处理
            result = await self.plugin_manager.execute_plugin(
                strategy["plugin_name"],
                "chat",  # 默认chat命令
                {"message": request.message, "context": context}
            )
            
            content = result.get("result", "插件执行完成") if result.get("success") else f"插件执行失败: {result.get('error')}"
            
            return ChatResponse(
                content=content,
                session_id=request.session_id or session_id,
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
                content=response["text"],
                session_id=request.session_id or session_id,
                model_used=ModelType.LOCAL_SMALL,
                reasoning=strategy["reasoning"],
                token_count=response.get("token_count", 0),
                latency_ms=response.get("latency_ms", 0)
            )
        
        elif strategy["use_cloud"]:
            # 使用云端模型
            response = await self.cloud_client.chat_completion(
                messages=[{"role": "user", "content": request.message}],
                model=request.preferred_model or "gemini-1.5-pro",
                max_tokens=request.max_tokens or 2048,
                temperature=request.temperature or 0.7
            )
            
            if "error" in response:
                # 云端调用失败，降级到本地模型
                logger.warning(f"云端模型调用失败，降级到本地模型: {response['error']}")
                return await self._fallback_to_local(request, strategy, session_id)
            
            return ChatResponse(
                content=response["content"],
                session_id=request.session_id or session_id,
                model_used=ModelType.CLOUD_LARGE,
                reasoning=strategy["reasoning"],
                token_count=response.get("token_count", 0)
            )
        
        else:
            # 默认使用本地模型
            return await self._fallback_to_local(request, strategy, session_id)
    
    async def _fallback_to_local(self, request: ChatRequest, strategy: Dict[str, Any], session_id: str) -> ChatResponse:
        """降级到本地模型"""
        try:
            response = await self.grpc_client.inference(
                prompt=request.message,
                model_type="chat",
                max_tokens=request.max_tokens or 1024,
                temperature=request.temperature or 0.7
            )
            return ChatResponse(
                content=response["text"],
                session_id=request.session_id or session_id,
                model_used=ModelType.LOCAL_SMALL,
                reasoning="云端模型不可用，使用本地模型",
                token_count=response.get("token_count", 0),
                latency_ms=response.get("latency_ms", 0)
            )
        except Exception as e:
            logger.error(f"本地模型也不可用: {e}")
            return ChatResponse(
                content="抱歉，目前所有AI模型都不可用，请稍后重试。",
                session_id=request.session_id or session_id,
                model_used=ModelType.LOCAL_SMALL,
                reasoning="所有模型不可用",
                error=str(e)
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