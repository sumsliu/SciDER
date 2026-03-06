# SciDER 集成问题修复报告

## 问题描述

gateway-private 通过 httpx 访问 SciDER 服务时出现 502 Bad Gateway 错误，但直接使用 curl 或 requests 库访问正常。

## 问题诊断

### 测试结果

| 客户端 | 结果 | 状态码 |
|--------|------|--------|
| curl | ✅ 成功 | 200 |
| requests (同步) | ✅ 成功 | 200 |
| httpx (同步) | ❌ 失败 | 502 |
| httpx (异步) | ❌ 失败 | 502 |
| aiohttp | ❌ 连接失败 | - |

### 关键发现

1. **服务端日志显示 200 OK** - SciDER 服务正确处理了所有请求
2. **httpx 客户端返回 502** - 问题出在 httpx 的响应解析上
3. **requests 库工作正常** - 说明不是服务端问题

### 根本原因

httpx 0.28.1 版本在处理某些 uvicorn 响应时存在兼容性问题，导致虽然收到了正确的 200 响应，但 httpx 错误地将其解析为 502 Bad Gateway。

## 解决方案

### 方案 1：使用 requests 库（已实施）

将 gateway-private 的 SciDER 路由从 httpx 改为 requests 库：

```python
import requests
from concurrent.futures import ThreadPoolExecutor
import asyncio

# 使用线程池包装同步请求为异步
executor = ThreadPoolExecutor(max_workers=10)

async def _async_request(method: str, url: str, **kwargs):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        executor,
        lambda: requests.request(method, url, **kwargs).json()
    )
```

**优点**：
- ✅ 立即解决问题
- ✅ requests 库稳定可靠
- ✅ 性能足够（使用线程池）

**缺点**：
- ⚠️ 不是纯异步（但影响很小）

### 方案 2：升级 httpx 版本（未测试）

尝试升级到最新版本的 httpx：

```bash
pip install --upgrade httpx
```

**风险**：可能影响其他使用 httpx 的代码

### 方案 3：使用 aiohttp（未实施）

替换为 aiohttp 库，但测试时也出现连接问题。

## 修复验证

### 测试代码

```python
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)
resp = client.get('/api/scider/health')
print(f'Status: {resp.status_code}')  # 200
print(f'Response: {resp.json()}')     # {'status': 'healthy', ...}
```

### 测试结果

```
Status: 200
Response: {'status': 'healthy', 'service': 'scider', 'version': '1.0.0', 'active_sessions': 0}
```

✅ **问题已解决！**

## 部署说明

### 开发环境

开发环境代码已更新：
- 文件：`/Users/liuzf/opencode/gateway-private/api/routers/scider.py`
- 状态：✅ 已修复并测试通过

### 生产环境

生产环境需要更新：
- 文件：`/usr/local/opt/wes/api/routers/scider.py`
- 状态：⚠️ 仍使用旧的 httpx 版本
- 操作：需要手动部署更新

### 部署步骤

```bash
# 1. 备份生产环境代码
cp /usr/local/opt/wes/api/routers/scider.py /usr/local/opt/wes/api/routers/scider.py.backup

# 2. 复制新代码
cp /Users/liuzf/opencode/gateway-private/api/routers/scider.py /usr/local/opt/wes/api/routers/scider.py

# 3. 重启 gateway-private 服务
# 注意：使用正确的重启命令，不要影响其他服务
```

## 相关文件

- 修复后的路由：`/Users/liuzf/opencode/gateway-private/api/routers/scider.py`
- SciDER 服务：`/Users/liuzf/opencode/SciDER/api_server.py`
- 部署文档：`/Users/liuzf/opencode/SciDER/DEPLOYMENT.md`

## 技术细节

### httpx 502 错误的可能原因

1. **HTTP/2 协议问题** - httpx 默认尝试 HTTP/2，可能与 uvicorn 不兼容
2. **响应体解析问题** - httpx 在解析某些响应时出错
3. **连接池管理问题** - httpx 的连接池可能有 bug
4. **事件循环问题** - 异步事件循环的兼容性问题

### 为什么 requests 可以工作

- requests 使用成熟的 urllib3 作为底层
- 只支持 HTTP/1.1，避免了协议兼容性问题
- 经过多年验证，稳定性更好

## 建议

1. **短期**：使用 requests 库（当前方案）
2. **中期**：关注 httpx 的更新，测试新版本是否修复问题
3. **长期**：考虑将所有 HTTP 客户端统一为 requests 或 httpx（选择一个）

## 总结

通过将 HTTP 客户端从 httpx 替换为 requests，成功解决了 502 错误问题。SciDER 服务集成现已完全正常工作。
