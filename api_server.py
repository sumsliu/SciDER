"""
SciDER FastAPI Service

独立的 FastAPI 服务，暴露 SciDER 工作流接口。
运行在 Python 3.13 环境，端口 8003。

启动命令：
    source .venv/bin/activate
    uvicorn api_server:app --host 127.0.0.1 --port 8003 --reload
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from pathlib import Path
import asyncio
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Dict, Any
from datetime import datetime

from scider.workflows.full_workflow import run_full_workflow

app = FastAPI(
    title="SciDER Service",
    version="1.0.0",
    description="Scientific Discovery and Experimentation with Reasoning"
)

# 全局会话存储
sessions: Dict[str, Dict[str, Any]] = {}

class WorkflowRequest(BaseModel):
    """SciDER 工作流请求"""
    data_path: str = Field(..., description="数据文件或目录路径")
    workspace_path: str = Field(..., description="工作空间目录路径")
    user_query: str = Field(..., description="研究问题或分析目标")
    repository_url: Optional[str] = Field(None, description="可选的代码仓库 URL")
    max_revisions: int = Field(5, description="ExperimentAgent 最大修订次数")
    data_agent_recursion_limit: int = Field(100, description="DataAgent 递归限制")
    experiment_agent_recursion_limit: int = Field(100, description="ExperimentAgent 递归限制")
    session_name: Optional[str] = Field(None, description="自定义会话名称")
    data_desc: Optional[str] = Field(None, description="数据的额外描述")

class WorkflowResponse(BaseModel):
    """工作流响应"""
    session_id: str
    status: str
    message: str
    workspace_path: str

class SessionStatus(BaseModel):
    """会话状态"""
    session_id: str
    status: str
    created_at: str
    workspace_path: str
    final_status: Optional[str] = None
    final_summary: Optional[str] = None
    error: Optional[str] = None

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "scider",
        "version": "1.0.0",
        "active_sessions": len([s for s in sessions.values() if s["status"] == "running"])
    }

@app.post("/workflow", response_model=WorkflowResponse)
async def execute_workflow(request: WorkflowRequest, background_tasks: BackgroundTasks):
    """
    执行 SciDER 工作流

    工作流将在后台异步执行，立即返回 session_id。
    使用 GET /sessions/{session_id} 查询执行状态。
    """
    # 验证数据路径
    data_path = Path(request.data_path)
    if not data_path.exists():
        raise HTTPException(
            status_code=400,
            detail=f"数据路径不存在: {request.data_path}"
        )

    # 创建工作空间
    workspace = Path(request.workspace_path)
    workspace.mkdir(parents=True, exist_ok=True)

    # 生成会话 ID
    session_id = str(uuid.uuid4())

    # 初始化会话状态
    sessions[session_id] = {
        "session_id": session_id,
        "status": "running",
        "created_at": datetime.now().isoformat(),
        "workspace_path": str(workspace.absolute()),
        "final_status": None,
        "final_summary": None,
        "error": None
    }

    # 在后台执行工作流
    background_tasks.add_task(
        run_workflow_background,
        session_id=session_id,
        request=request
    )

    return WorkflowResponse(
        session_id=session_id,
        status="started",
        message="SciDER 工作流已启动，正在后台执行",
        workspace_path=str(workspace.absolute())
    )

def run_workflow_background(session_id: str, request: WorkflowRequest):
    """后台执行工作流"""
    try:
        # 执行 SciDER 工作流
        result = run_full_workflow(
            data_path=request.data_path,
            workspace_path=request.workspace_path,
            user_query=request.user_query,
            repo_source=request.repository_url,
            max_revisions=request.max_revisions,
            data_agent_recursion_limit=request.data_agent_recursion_limit,
            experiment_agent_recursion_limit=request.experiment_agent_recursion_limit,
            session_name=request.session_name,
            data_desc=request.data_desc,
        )

        # 更新会话状态
        sessions[session_id].update({
            "status": "completed",
            "final_status": result.final_status,
            "final_summary": result.final_summary
        })

    except Exception as e:
        # 记录错误
        sessions[session_id].update({
            "status": "failed",
            "error": str(e)
        })

@app.get("/sessions/{session_id}", response_model=SessionStatus)
async def get_session_status(session_id: str):
    """获取会话状态"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail=f"会话不存在: {session_id}")

    return SessionStatus(**sessions[session_id])

@app.get("/sessions")
async def list_sessions():
    """列出所有会话"""
    return {"sessions": list(sessions.values())}

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """删除会话记录"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail=f"会话不存在: {session_id}")

    del sessions[session_id]
    return {"message": f"会话 {session_id} 已删除"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8003)
