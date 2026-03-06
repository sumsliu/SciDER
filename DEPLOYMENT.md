# SciDER 服务部署文档

## 概述

SciDER (Scientific Discovery and Experimentation with Reasoning) 是一个多智能体科学实验自动化框架。本文档描述如何将 SciDER 集成到 gateway-private 后端架构中。

## 架构设计

```
┌─────────────────────────────────────────────────────┐
│  gateway-private (Python 3.11, port 8002)           │
│  ├─ FastAPI 主服务                                   │
│  └─ /api/scider/* 路由 → HTTP 转发到 SciDER 服务    │
└─────────────────────────────────────────────────────┘
                    ↓ HTTP (localhost:8003)
┌─────────────────────────────────────────────────────┐
│  SciDER 服务 (Python 3.13, port 8003)               │
│  ├─ uv 虚拟环境: .venv                               │
│  ├─ FastAPI 服务暴露 SciDER 接口                     │
│  └─ 常驻后台，接收工作流请求                          │
└─────────────────────────────────────────────────────┘
```

## 环境要求

- **Python 版本**: 3.13+ (SciDER 要求)
- **包管理器**: uv (SciDER 官方推荐)
- **依赖**: FastAPI, uvicorn, httpx

## 安装步骤

### 1. 安装 SciDER 依赖

```bash
cd /Users/liuzf/opencode/SciDER

# 使用 uv 安装依赖（macOS）
uv sync --extra mac

# 验证安装
.venv/bin/python -c "from scider.workflows.full_workflow import run_full_workflow; print('✓ SciDER 安装成功')"
```

### 2. 安装 FastAPI 依赖

```bash
cd /Users/liuzf/opencode/SciDER

# 使用 uv 安装 FastAPI 和 uvicorn
uv pip install fastapi 'uvicorn[standard]'
```

### 3. 验证文件

确保以下文件存在：
- `/Users/liuzf/opencode/SciDER/api_server.py` - SciDER FastAPI 服务
- `/Users/liuzf/opencode/SciDER/start_scider_service.sh` - 启动脚本
- `/Users/liuzf/opencode/gateway-private/api/routers/scider.py` - gateway-private 路由

## 启动服务

### 方式 1：使用启动脚本（推荐）

```bash
cd /Users/liuzf/opencode/SciDER
bash start_scider_service.sh
```

### 方式 2：手动启动

```bash
cd /Users/liuzf/opencode/SciDER
.venv/bin/python -m uvicorn api_server:app --host 127.0.0.1 --port 8003
```

### 方式 3：后台运行

```bash
cd /Users/liuzf/opencode/SciDER
nohup .venv/bin/python -m uvicorn api_server:app --host 127.0.0.1 --port 8003 > /tmp/scider_service.log 2>&1 &
```

## 测试

### 1. 测试 SciDER 服务

```bash
# 健康检查
curl http://127.0.0.1:8003/health

# 列出会话
curl http://127.0.0.1:8003/sessions

# 执行工作流（示例）
curl -X POST http://127.0.0.1:8003/workflow \
  -H "Content-Type: application/json" \
  -d '{
    "data_path": "/path/to/data.csv",
    "workspace_path": "./workspace",
    "user_query": "Analyze this dataset"
  }'
```

### 2. 测试 gateway-private 集成

```bash
# 通过 gateway-private 访问 SciDER
curl http://127.0.0.1:8002/api/scider/health

# 通过 gateway-private 执行工作流
curl -X POST http://127.0.0.1:8002/api/scider/workflow \
  -H "Content-Type: application/json" \
  -d '{
    "data_path": "/path/to/data.csv",
    "workspace_path": "./workspace",
    "user_query": "Analyze this dataset"
  }'
```

## API 端点

### SciDER 服务端点 (port 8003)

- `GET /health` - 健康检查
- `POST /workflow` - 执行工作流
- `GET /sessions` - 列出所有会话
- `GET /sessions/{session_id}` - 获取会话状态
- `DELETE /sessions/{session_id}` - 删除会话

### gateway-private 端点 (port 8002)

- `GET /api/scider/health` - 健康检查（转发）
- `POST /api/scider/workflow` - 执行工作流（转发）
- `GET /api/scider/sessions` - 列出会话（转发）
- `GET /api/scider/sessions/{session_id}` - 获取会话状态（转发）
- `DELETE /api/scider/sessions/{session_id}` - 删除会话（转发）

## 工作流参数

```json
{
  "data_path": "string",                    // 必需：数据文件路径
  "workspace_path": "string",               // 必需：工作空间路径
  "user_query": "string",                   // 必需：研究问题
  "repository_url": "string",               // 可选：代码仓库 URL
  "max_revisions": 5,                       // 可选：最大修订次数
  "data_agent_recursion_limit": 100,        // 可选：DataAgent 递归限制
  "experiment_agent_recursion_limit": 100,  // 可选：ExperimentAgent 递归限制
  "session_name": "string",                 // 可选：会话名称
  "data_desc": "string"                     // 可选：数据描述
}
```

## 故障排查

### 问题 1：SciDER 服务无法启动

**症状**: `ModuleNotFoundError: No module named 'xxx'`

**解决方案**:
```bash
cd /Users/liuzf/opencode/SciDER
rm -rf .venv
uv sync --extra mac
uv pip install fastapi 'uvicorn[standard]'
```

### 问题 2：端口被占用

**症状**: `[Errno 48] error while attempting to bind on address`

**解决方案**:
```bash
# 查找占用端口的进程
lsof -i :8003

# 停止进程
kill -9 <PID>
```

### 问题 3：gateway-private 无法连接 SciDER

**症状**: `502 Bad Gateway`

**检查步骤**:
1. 确认 SciDER 服务正在运行: `curl http://127.0.0.1:8003/health`
2. 检查防火墙设置
3. 查看 gateway-private 日志

## 维护

### 查看日志

```bash
# SciDER 服务日志
tail -f /tmp/scider_service.log

# gateway-private 日志
tail -f /usr/local/opt/wes/logs/gateway.log
```

### 停止服务

```bash
# 停止 SciDER 服务
lsof -ti:8003 | xargs kill

# 停止 gateway-private（不要随意停止生产服务！）
# lsof -ti:8002 | xargs kill
```

### 重启服务

```bash
# 重启 SciDER 服务
cd /Users/liuzf/opencode/SciDER
bash start_scider_service.sh
```

## 注意事项

1. **不要停止 8002 端口的服务** - 这是 gateway-private 的生产服务
2. **SciDER 使用 Python 3.13** - 与 gateway-private 的 Python 3.11 环境隔离
3. **使用 uv 管理依赖** - 这是 SciDER 官方推荐的方式
4. **工作流在后台执行** - 使用 session_id 查询状态
5. **定期清理会话** - 避免内存占用过高

## 相关文件

- SciDER 项目: `/Users/liuzf/opencode/SciDER/`
- SciDER API 服务: `/Users/liuzf/opencode/SciDER/api_server.py`
- gateway-private 路由: `/Users/liuzf/opencode/gateway-private/api/routers/scider.py`
- 启动脚本: `/Users/liuzf/opencode/SciDER/start_scider_service.sh`
- 日志文件: `/tmp/scider_service.log`
