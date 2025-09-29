"""
智能路由策略系统
"""
import asyncio
import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from core.adapters import UnifiedChatRequest, ModelInfo, ProviderType, EngineType


logger = logging.getLogger(__name__)


class TaskComplexity(str, Enum):
    """任务复杂度"""
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"


class RouteStrategy(str, Enum):
    """路由策略"""
    LOCAL_FIRST = "local_first"
    CLOUD_FIRST = "cloud_first"
    SMART_ROUTE = "smart_route"
    COST_OPTIMIZED = "cost_optimized"
    PERFORMANCE_OPTIMIZED = "performance_optimized"


@dataclass
class RoutingDecision:
    """路由决策结果"""
    provider: str
    model: str
    reasoning: str
    confidence: float
    estimated_cost: float = 0.0
    estimated_latency: float = 0.0
    fallback_options: List[str] = None
    
    def __post_init__(self):
        if self.fallback_options is None:
            self.fallback_options = []


@dataclass
class ModelCapability:
    """模型能力评估"""
    model_id: str
    provider: str
    engine: str
    
    # 能力评分 (0.0-1.0)
    general_chat: float = 0.0
    coding: float = 0.0
    reasoning: float = 0.0
    creative_writing: float = 0.0
    translation: float = 0.0
    math: float = 0.0
    analysis: float = 0.0
    
    # 性能指标
    context_length: int = 4096
    speed_score: float = 0.0  # tokens/second normalized
    cost_score: float = 0.0   # cost per token normalized
    reliability: float = 0.0  # success rate
    
    # 限制
    requires_internet: bool = True
    supports_streaming: bool = True
    max_concurrent: int = 100


class TaskAnalyzer:
    """任务分析器"""
    
    def __init__(self):
        # 复杂度关键词
        self.simple_keywords = [
            "你好", "谢谢", "再见", "是的", "不是", "好的", "没问题",
            "hello", "thanks", "bye", "yes", "no", "ok"
        ]
        
        self.medium_keywords = [
            "什么是", "如何", "怎么", "为什么", "解释", "说明", "介绍",
            "what", "how", "why", "explain", "describe", "tell me"
        ]
        
        self.complex_keywords = [
            "分析", "设计", "编程", "代码", "算法", "架构", "创作", "写一个",
            "详细分析", "深入探讨", "全面评估", "系统设计", "方案制定",
            "analyze", "design", "code", "program", "algorithm", "create", "write"
        ]
        
        # 功能需求关键词
        self.function_keywords = {
            "coding": ["代码", "编程", "程序", "脚本", "函数", "code", "program", "script", "function"],
            "math": ["计算", "数学", "公式", "equation", "calculate", "math", "formula"],
            "creative": ["创作", "写作", "故事", "诗歌", "creative", "write", "story", "poem"],
            "translation": ["翻译", "translate", "转换", "convert"],
            "analysis": ["分析", "评估", "研究", "analyze", "evaluate", "research"],
            "reasoning": ["推理", "逻辑", "判断", "reason", "logic", "judge"]
        }
        
        # 实时信息需求关键词
        self.realtime_keywords = [
            "最新", "今天", "现在", "当前", "实时", "新闻", "天气", "股价",
            "latest", "today", "now", "current", "real-time", "news", "weather"
        ]
    
    async def analyze_task(self, request: UnifiedChatRequest) -> Dict[str, Any]:
        """分析任务特征"""
        message_text = " ".join([msg.get("content", "") for msg in request.messages])
        message_lower = message_text.lower()
        
        # 基本信息
        analysis = {
            "complexity": self._analyze_complexity(message_text),
            "required_functions": self._detect_required_functions(message_lower),
            "requires_internet": self._requires_internet(message_lower),
            "estimated_tokens": self._estimate_response_tokens(message_text),
            "language": self._detect_language(message_text),
            "urgency": self._analyze_urgency(message_lower)
        }
        
        return analysis
    
    def _analyze_complexity(self, text: str) -> TaskComplexity:
        """分析任务复杂度"""
        text_lower = text.lower()
        
        # 简单任务检测
        simple_score = sum(1 for keyword in self.simple_keywords if keyword in text_lower)
        if simple_score > 0 and len(text) < 50:
            return TaskComplexity.SIMPLE
        
        # 复杂任务检测
        complex_score = sum(1 for keyword in self.complex_keywords if keyword in text_lower)
        if complex_score > 0 or len(text) > 500:
            return TaskComplexity.COMPLEX
        
        # 中等复杂度检测
        medium_score = sum(1 for keyword in self.medium_keywords if keyword in text_lower)
        if medium_score > 0 or len(text) > 100:
            return TaskComplexity.MEDIUM
        
        # 默认为简单
        return TaskComplexity.SIMPLE
    
    def _detect_required_functions(self, text: str) -> List[str]:
        """检测需要的功能"""
        functions = []
        
        for func, keywords in self.function_keywords.items():
            if any(keyword in text for keyword in keywords):
                functions.append(func)
        
        return functions
    
    def _requires_internet(self, text: str) -> bool:
        """检测是否需要联网"""
        return any(keyword in text for keyword in self.realtime_keywords)
    
    def _estimate_response_tokens(self, text: str) -> int:
        """估算响应token数"""
        input_tokens = len(text.split()) * 1.3  # 估算输入token
        
        # 根据输入长度和复杂度估算输出长度
        if len(text) < 50:
            return int(input_tokens * 0.5)  # 简短回复
        elif len(text) < 200:
            return int(input_tokens * 1.0)  # 相当长度回复
        else:
            return int(input_tokens * 1.5)  # 详细回复
    
    def _detect_language(self, text: str) -> str:
        """检测语言"""
        # 简单的语言检测
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        total_chars = len(text)
        
        if chinese_chars / max(total_chars, 1) > 0.3:
            return "zh"
        else:
            return "en"
    
    def _analyze_urgency(self, text: str) -> str:
        """分析紧急程度"""
        urgent_keywords = ["紧急", "急", "马上", "立即", "urgent", "asap", "immediately"]
        
        if any(keyword in text for keyword in urgent_keywords):
            return "high"
        else:
            return "normal"


class IntelligentRouter:
    """智能路由器"""
    
    def __init__(self, model_manager, gpu_manager=None):
        self.model_manager = model_manager
        self.gpu_manager = gpu_manager
        self.task_analyzer = TaskAnalyzer()
        
        # 路由配置
        self.strategy = RouteStrategy.SMART_ROUTE
        self.complexity_threshold = 0.7
        self.local_preference = 0.6  # 本地优先权重
        self.cost_weight = 0.3
        self.performance_weight = 0.4
        self.reliability_weight = 0.3
        
        # 模型能力数据库
        self.model_capabilities: Dict[str, ModelCapability] = {}
        self._initialize_model_capabilities()
        
        # 性能统计
        self.performance_stats: Dict[str, Dict[str, float]] = {}
        self.fallback_history: List[Dict[str, Any]] = []
    
    def _initialize_model_capabilities(self):
        """初始化模型能力数据库"""
        # OpenAI模型能力
        self.model_capabilities.update({
            "gpt-4": ModelCapability(
                model_id="gpt-4",
                provider="openai",
                engine="cloud",
                general_chat=0.95,
                coding=0.90,
                reasoning=0.95,
                creative_writing=0.85,
                translation=0.90,
                math=0.88,
                analysis=0.92,
                context_length=8192,
                speed_score=0.7,
                cost_score=0.3,  # 较贵
                reliability=0.95,
                requires_internet=True
            ),
            "gpt-3.5-turbo": ModelCapability(
                model_id="gpt-3.5-turbo",
                provider="openai",
                engine="cloud",
                general_chat=0.85,
                coding=0.75,
                reasoning=0.80,
                creative_writing=0.75,
                translation=0.85,
                math=0.75,
                analysis=0.80,
                context_length=4096,
                speed_score=0.85,
                cost_score=0.8,  # 较便宜
                reliability=0.92,
                requires_internet=True
            ),
            
            # Gemini模型能力
            "gemini-1.5-pro": ModelCapability(
                model_id="gemini-1.5-pro",
                provider="gemini",
                engine="cloud",
                general_chat=0.90,
                coding=0.85,
                reasoning=0.90,
                creative_writing=0.88,
                translation=0.92,
                math=0.85,
                analysis=0.90,
                context_length=2097152,  # 2M tokens
                speed_score=0.75,
                cost_score=0.7,
                reliability=0.90,
                requires_internet=True
            ),
            
            # Claude模型能力
            "claude-3-sonnet-20240229": ModelCapability(
                model_id="claude-3-sonnet-20240229",
                provider="claude",
                engine="cloud",
                general_chat=0.92,
                coding=0.88,
                reasoning=0.93,
                creative_writing=0.90,
                translation=0.88,
                math=0.82,
                analysis=0.95,
                context_length=200000,
                speed_score=0.72,
                cost_score=0.5,
                reliability=0.93,
                requires_internet=True
            ),
            
            # 本地模型能力
            "qwen3:4b": ModelCapability(
                model_id="qwen3:4b",
                provider="llamacpp",
                engine="local",
                general_chat=0.75,
                coding=0.70,
                reasoning=0.70,
                creative_writing=0.65,
                translation=0.80,
                math=0.65,
                analysis=0.70,
                context_length=4096,
                speed_score=0.90,  # 本地速度快
                cost_score=1.0,   # 免费
                reliability=0.85,
                requires_internet=False
            ),
            "qwen2.5:7b": ModelCapability(
                model_id="qwen2.5:7b",
                provider="ollama",
                engine="local",
                general_chat=0.80,
                coding=0.75,
                reasoning=0.75,
                creative_writing=0.70,
                translation=0.85,
                math=0.70,
                analysis=0.75,
                context_length=8192,
                speed_score=0.85,
                cost_score=1.0,
                reliability=0.88,
                requires_internet=False
            )
        })
    
    async def route_request(self, request: UnifiedChatRequest) -> RoutingDecision:
        """智能路由决策"""
        try:
            # 1. 用户明确指定provider
            if request.provider and request.provider != "auto":
                return await self._route_by_provider(request)
            
            # 2. 用户明确指定model
            if request.model and request.model in self.model_capabilities:
                capability = self.model_capabilities[request.model]
                return RoutingDecision(
                    provider=capability.provider,
                    model=request.model,
                    reasoning="用户指定模型",
                    confidence=1.0,
                    fallback_options=await self._get_fallback_options(request.model)
                )
            
            # 3. 任务分析
            task_analysis = await self.task_analyzer.analyze_task(request)
            
            # 4. 智能路由决策
            return await self._smart_route(request, task_analysis)
            
        except Exception as e:
            logger.error(f"路由决策失败: {e}")
            # 返回默认路由
            return RoutingDecision(
                provider="llamacpp",
                model="qwen3:4b",
                reasoning=f"路由决策失败，使用默认本地模型: {str(e)}",
                confidence=0.1
            )
    
    async def _route_by_provider(self, request: UnifiedChatRequest) -> RoutingDecision:
        """根据指定provider路由"""
        adapter = self.model_manager.get_adapter_manager().get_adapter_by_provider(request.provider)
        
        if not adapter or not adapter.is_healthy():
            # Provider不可用，降级
            fallback = await self._find_fallback_provider(request.provider)
            return RoutingDecision(
                provider=fallback["provider"],
                model=fallback["model"],
                reasoning=f"指定的 {request.provider} 不可用，降级到 {fallback['provider']}",
                confidence=0.7,
                fallback_options=[request.provider]
            )
        
        # 选择该provider的最佳模型
        available_models = await adapter.get_available_models()
        if not available_models:
            fallback = await self._find_fallback_provider(request.provider)
            return RoutingDecision(
                provider=fallback["provider"],
                model=fallback["model"],
                reasoning=f"{request.provider} 无可用模型，降级到 {fallback['provider']}",
                confidence=0.6
            )
        
        # 选择最适合的模型
        best_model = available_models[0]
        for model in available_models:
            if model.id in self.model_capabilities:
                best_model = model
                break
        
        return RoutingDecision(
            provider=request.provider,
            model=best_model.id,
            reasoning=f"用户指定provider: {request.provider}",
            confidence=0.9
        )
    
    async def _smart_route(self, request: UnifiedChatRequest, task_analysis: Dict[str, Any]) -> RoutingDecision:
        """智能路由决策"""
        complexity = task_analysis["complexity"]
        required_functions = task_analysis["required_functions"]
        requires_internet = task_analysis["requires_internet"]
        estimated_tokens = task_analysis["estimated_tokens"]
        
        # 获取可用模型
        available_models = await self.model_manager.get_available_models()
        if not available_models:
            return RoutingDecision(
                provider="llamacpp",
                model="qwen3:4b",
                reasoning="无可用模型，使用默认配置",
                confidence=0.1
            )
        
        # 评分所有可用模型
        model_scores = []
        
        for model_info in available_models:
            if model_info.id in self.model_capabilities:
                capability = self.model_capabilities[model_info.id]
                score = await self._score_model(capability, task_analysis)
                
                model_scores.append({
                    "model": model_info.id,
                    "provider": capability.provider,
                    "score": score,
                    "capability": capability
                })
        
        if not model_scores:
            # 没有已知能力的模型，选择第一个可用的
            model_info = available_models[0]
            return RoutingDecision(
                provider=model_info.provider,
                model=model_info.id,
                reasoning="使用首个可用模型",
                confidence=0.5
            )
        
        # 按评分排序
        model_scores.sort(key=lambda x: x["score"], reverse=True)
        best_model = model_scores[0]
        
        # 生成决策原因
        reasoning = self._generate_reasoning(best_model, task_analysis)
        
        # 获取备选方案
        fallback_options = [m["model"] for m in model_scores[1:3]]
        
        return RoutingDecision(
            provider=best_model["provider"],
            model=best_model["model"],
            reasoning=reasoning,
            confidence=min(best_model["score"], 1.0),
            estimated_cost=self._estimate_cost(best_model["capability"], estimated_tokens),
            estimated_latency=self._estimate_latency(best_model["capability"], estimated_tokens),
            fallback_options=fallback_options
        )
    
    async def _score_model(self, capability: ModelCapability, task_analysis: Dict[str, Any]) -> float:
        """为模型评分"""
        score = 0.0
        
        # 基础能力评分
        complexity = task_analysis["complexity"]
        required_functions = task_analysis["required_functions"]
        requires_internet = task_analysis["requires_internet"]
        
        # 复杂度匹配
        if complexity == TaskComplexity.SIMPLE:
            score += capability.general_chat * 0.4
        elif complexity == TaskComplexity.MEDIUM:
            score += (capability.general_chat + capability.reasoning) * 0.3
        else:  # COMPLEX
            score += (capability.reasoning + capability.analysis) * 0.4
        
        # 功能需求匹配
        function_scores = {
            "coding": capability.coding,
            "math": capability.math,
            "creative": capability.creative_writing,
            "translation": capability.translation,
            "analysis": capability.analysis,
            "reasoning": capability.reasoning
        }
        
        for func in required_functions:
            if func in function_scores:
                score += function_scores[func] * 0.2
        
        # 联网需求
        if requires_internet and not capability.requires_internet:
            score *= 0.3  # 大幅降分
        elif not requires_internet and not capability.requires_internet:
            score *= 1.2  # 本地处理加分
        
        # 性能因素
        if self.strategy == RouteStrategy.PERFORMANCE_OPTIMIZED:
            score += capability.speed_score * self.performance_weight
        elif self.strategy == RouteStrategy.COST_OPTIMIZED:
            score += capability.cost_score * self.cost_weight
        else:
            # 平衡模式
            score += (capability.speed_score * 0.3 + 
                     capability.cost_score * 0.3 + 
                     capability.reliability * 0.4)
        
        # 本地优先策略
        if capability.engine == "local" and self.strategy in [RouteStrategy.LOCAL_FIRST, RouteStrategy.SMART_ROUTE]:
            score *= (1.0 + self.local_preference)
        
        # GPU可用性加分
        if capability.engine == "local" and self.gpu_manager and self.gpu_manager.is_gpu_available():
            score *= 1.3
        
        return score
    
    def _generate_reasoning(self, best_model: Dict[str, Any], task_analysis: Dict[str, Any]) -> str:
        """生成决策原因"""
        capability = best_model["capability"]
        reasons = []
        
        # 复杂度原因
        complexity = task_analysis["complexity"]
        if complexity == TaskComplexity.SIMPLE and capability.engine == "local":
            reasons.append("简单任务使用本地模型")
        elif complexity == TaskComplexity.COMPLEX and capability.engine == "cloud":
            reasons.append("复杂任务使用云端大模型")
        
        # 功能需求原因
        required_functions = task_analysis["required_functions"]
        if "coding" in required_functions and capability.coding > 0.8:
            reasons.append("编程任务选择代码能力强的模型")
        if "math" in required_functions and capability.math > 0.8:
            reasons.append("数学任务选择计算能力强的模型")
        if "creative" in required_functions and capability.creative_writing > 0.8:
            reasons.append("创作任务选择创意能力强的模型")
        
        # 联网需求原因
        if task_analysis["requires_internet"]:
            reasons.append("需要最新信息，使用云端模型")
        elif not task_analysis["requires_internet"] and capability.engine == "local":
            reasons.append("无需联网，优先本地模型")
        
        # 性能原因
        if capability.speed_score > 0.8:
            reasons.append("响应速度快")
        if capability.cost_score > 0.8:
            reasons.append("成本效益高")
        if capability.reliability > 0.9:
            reasons.append("稳定性好")
        
        return "；".join(reasons) if reasons else f"最佳匹配模型 {best_model['model']}"
    
    def _estimate_cost(self, capability: ModelCapability, tokens: int) -> float:
        """估算成本"""
        if capability.engine == "local":
            return 0.0  # 本地模型免费
        
        # 云端模型成本估算（简化）
        base_costs = {
            "gpt-4": 0.03,  # per 1k tokens
            "gpt-3.5-turbo": 0.002,
            "gemini-1.5-pro": 0.0035,
            "claude-3-sonnet-20240229": 0.003
        }
        
        cost_per_1k = base_costs.get(capability.model_id, 0.002)
        return (tokens / 1000) * cost_per_1k
    
    def _estimate_latency(self, capability: ModelCapability, tokens: int) -> float:
        """估算延迟"""
        if capability.engine == "local":
            # 本地模型延迟主要取决于GPU性能
            if self.gpu_manager and self.gpu_manager.is_gpu_available():
                return tokens / 50  # GPU加速，50 tokens/second
            else:
                return tokens / 10  # CPU模式，10 tokens/second
        else:
            # 云端模型延迟包括网络延迟
            base_latency = 500  # 网络延迟500ms
            generation_time = tokens / (capability.speed_score * 30)  # 根据速度评分计算
            return base_latency + generation_time * 1000
    
    async def _find_fallback_provider(self, failed_provider: str) -> Dict[str, str]:
        """寻找备选provider"""
        # 备选顺序
        fallback_order = {
            "openai": ["gemini", "claude", "llamacpp", "ollama"],
            "gemini": ["openai", "claude", "llamacpp", "ollama"],
            "claude": ["openai", "gemini", "llamacpp", "ollama"],
            "llamacpp": ["ollama", "gemini", "openai", "claude"],
            "ollama": ["llamacpp", "gemini", "openai", "claude"]
        }
        
        for provider in fallback_order.get(failed_provider, ["llamacpp"]):
            adapter = self.model_manager.get_adapter_manager().get_adapter_by_provider(provider)
            if adapter and adapter.is_healthy():
                models = await adapter.get_available_models()
                if models:
                    return {"provider": provider, "model": models[0].id}
        
        # 最终备选
        return {"provider": "llamacpp", "model": "qwen3:4b"}
    
    async def _get_fallback_options(self, primary_model: str) -> List[str]:
        """获取备选模型"""
        available_models = await self.model_manager.get_available_models()
        
        # 排除主模型，返回可用的备选模型
        fallback_models = [m.id for m in available_models if m.id != primary_model]
        
        # 按能力评分排序（简化实现）
        return fallback_models[:3]
    
    def update_strategy(self, strategy: RouteStrategy):
        """更新路由策略"""
        self.strategy = strategy
        logger.info(f"路由策略已更新为: {strategy.value}")
    
    def update_preferences(self, **kwargs):
        """更新路由偏好"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        logger.info(f"路由偏好已更新: {kwargs}")
    
    async def record_performance(self, model: str, latency: float, success: bool):
        """记录性能数据"""
        if model not in self.performance_stats:
            self.performance_stats[model] = {
                "total_requests": 0,
                "successful_requests": 0,
                "total_latency": 0.0,
                "avg_latency": 0.0,
                "success_rate": 0.0
            }
        
        stats = self.performance_stats[model]
        stats["total_requests"] += 1
        
        if success:
            stats["successful_requests"] += 1
            stats["total_latency"] += latency
            stats["avg_latency"] = stats["total_latency"] / stats["successful_requests"]
        
        stats["success_rate"] = stats["successful_requests"] / stats["total_requests"]
        
        # 更新模型能力数据
        if model in self.model_capabilities:
            capability = self.model_capabilities[model]
            capability.reliability = stats["success_rate"]
            # 更新速度评分（简化）
            if capability.engine == "local" and stats["avg_latency"] > 0:
                capability.speed_score = min(1.0, 1000 / stats["avg_latency"])
    
    def get_performance_stats(self) -> Dict[str, Dict[str, float]]:
        """获取性能统计"""
        return self.performance_stats.copy()