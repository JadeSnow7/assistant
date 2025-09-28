"""
API路由处理
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from typing import List, Optional
import logging
import json

from models.schemas import (
    ChatRequest, ChatResponse, TaskRequest, TaskResponse,
    PluginInfo, SystemStatus, MemoryQuery, MemoryResponse
)
from agent.orchestrator import AgentOrchestrator
from core.dependencies import get_orchestrator, get_current_user


logger = logging.getLogger(__name__)

api_router = APIRouter()


@api_router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
    current_user: str = Depends(get_current_user)
):
    """
    聊天接口 - 主要的AI对话入口
    """
    try:
        response = await orchestrator.process_chat(request)
        return response
    except Exception as e:
        logger.error(f"聊天处理失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
    current_user: str = Depends(get_current_user)
):
    """
    流式聊天接口 - 实时流式响应
    """
    async def generate_stream():
        try:
            async for chunk in orchestrator.process_chat_stream(request):
                yield f"data: {json.dumps(chunk.dict(), ensure_ascii=False)}\n\n"
        except Exception as e:
            error_chunk = {"error": str(e)}
            yield f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache"}
    )


@api_router.post("/tasks", response_model=TaskResponse)
async def create_task(
    request: TaskRequest,
    background_tasks: BackgroundTasks,
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
    current_user: str = Depends(get_current_user)
):
    """
    创建后台任务
    """
    try:
        task_id = await orchestrator.create_background_task(request)
        return TaskResponse(
            task_id=task_id,
            status="created",
            message="任务已创建"
        )
    except Exception as e:
        logger.error(f"创建任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task_status(
    task_id: str,
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
    current_user: str = Depends(get_current_user)
):
    """
    获取任务状态
    """
    try:
        status = await orchestrator.get_task_status(task_id)
        if not status:
            raise HTTPException(status_code=404, detail="任务不存在")
        return status
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/plugins", response_model=List[PluginInfo])
async def list_plugins(
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
    current_user: str = Depends(get_current_user)
):
    """
    获取插件列表
    """
    try:
        plugins = await orchestrator.plugin_manager.get_available_plugins()
        return plugins
    except Exception as e:
        logger.error(f"获取插件列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/plugins/{plugin_name}/enable")
async def enable_plugin(
    plugin_name: str,
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
    current_user: str = Depends(get_current_user)
):
    """
    启用插件
    """
    try:
        success = await orchestrator.plugin_manager.enable_plugin(plugin_name)
        if not success:
            raise HTTPException(status_code=400, detail="插件启用失败")
        return {"message": f"插件 {plugin_name} 已启用"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"启用插件失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/plugins/{plugin_name}/disable")
async def disable_plugin(
    plugin_name: str,
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
    current_user: str = Depends(get_current_user)
):
    """
    禁用插件
    """
    try:
        success = await orchestrator.plugin_manager.disable_plugin(plugin_name)
        if not success:
            raise HTTPException(status_code=400, detail="插件禁用失败")
        return {"message": f"插件 {plugin_name} 已禁用"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"禁用插件失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/system/status", response_model=SystemStatus)
async def get_system_status(
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
    current_user: str = Depends(get_current_user)
):
    """
    获取系统状态
    """
    try:
        # 获取系统资源信息
        system_info = await orchestrator.grpc_client.get_system_info()
        
        # 获取性能统计
        stats = orchestrator.get_stats()
        
        # 获取组件健康状态
        health_status = {
            "grpc_client": await orchestrator.grpc_client.health_check(),
            "memory_manager": orchestrator.memory_manager.is_healthy(),
            "plugin_manager": orchestrator.plugin_manager.is_healthy(),
            "cloud_client": orchestrator.cloud_client.is_healthy()
        }
        
        return SystemStatus(
            cpu_usage=system_info.cpu_usage,
            memory_usage=system_info.memory_usage,
            gpu_usage=system_info.gpu_usage,
            active_sessions=await orchestrator.memory_manager.get_active_session_count(),
            total_requests=stats["total_requests"],
            avg_response_time=stats["avg_response_time"],
            components_health=health_status,
            uptime_seconds=0  # TODO: 实现运行时间统计
        )
    except Exception as e:
        logger.error(f"获取系统状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/memory/query", response_model=MemoryResponse)
async def query_memory(
    query: MemoryQuery,
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
    current_user: str = Depends(get_current_user)
):
    """
    查询记忆内容
    """
    try:
        results = await orchestrator.memory_manager.search_memory(
            query.query_text,
            session_id=query.session_id,
            limit=query.limit
        )
        
        return MemoryResponse(
            results=results,
            total_count=len(results)
        )
    except Exception as e:
        logger.error(f"查询记忆失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.delete("/memory/session/{session_id}")
async def clear_session_memory(
    session_id: str,
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
    current_user: str = Depends(get_current_user)
):
    """
    清除会话记忆
    """
    try:
        success = await orchestrator.memory_manager.clear_session(session_id)
        if not success:
            raise HTTPException(status_code=400, detail="清除会话记忆失败")
        return {"message": f"会话 {session_id} 的记忆已清除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"清除会话记忆失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/models")
async def list_models(
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
    current_user: str = Depends(get_current_user)
):
    """
    获取可用模型列表
    """
    try:
        local_models = await orchestrator.grpc_client.get_available_models()
        cloud_models = await orchestrator.cloud_client.get_available_models()
        
        return {
            "local_models": local_models,
            "cloud_models": cloud_models
        }
    except Exception as e:
        logger.error(f"获取模型列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/config/update")
async def update_config(
    config: dict,
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
    current_user: str = Depends(get_current_user)
):
    """
    更新配置
    """
    try:
        # TODO: 实现配置更新逻辑
        return {"message": "配置更新成功"}
    except Exception as e:
        logger.error(f"更新配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))