# SciDER Message Validation Fix - Design Document

## 问题描述

OpenAI API 要求：任何包含 `tool_calls` 的 assistant 消息必须紧跟着对应的 tool 消息，响应每个 `tool_call_id`。

错误信息：
```
An assistant message with 'tool_calls' must be followed by tool messages
responding to each 'tool_call_id'. (insufficient tool messages following tool_calls message)
```

## 根本原因

在消息历史压缩或重试过程中，可能出现以下情况：
1. 历史压缩删除了 tool responses 但保留了带 tool_calls 的 assistant 消息
2. 消息序列在构建时出现不完整的 tool_calls/responses 配对
3. 重试逻辑使用了不完整的消息历史

## 解决方案设计

### 架构原则

1. **单一职责**：验证逻辑集中在一个地方
2. **DRY 原则**：避免代码重复
3. **关注点分离**：验证逻辑独立于业务逻辑
4. **可测试性**：纯函数，易于单元测试
5. **性能优化**：只在必要时验证（发送给 API 前）

### 实现方案

#### 1. 创建独立的验证模块

**文件**: `scider/core/message_utils.py`

**核心函数**: `validate_and_clean_messages(messages: list[dict]) -> list[dict]`

**功能**:
- 验证所有 `tool_call_id` 是否都有对应的 tool responses
- 移除不完整的 tool_calls/responses 序列
- 保持消息序列的完整性和连贯性

**优势**:
- 纯函数，无副作用
- 易于测试和维护
- 可复用于其他需要验证的场景

#### 2. 在 LLM 调用前验证

**文件**: `scider/core/llms.py`

**位置**: `_completion` 方法中，在发送给 OpenAI API 之前

```python
# Prepare messages
openai_messages = [msg.to_ll_message() for msg in messages]

# Validate and clean message sequence for OpenAI API compatibility
openai_messages = validate_and_clean_messages(openai_messages)
```

**优势**:
- 在最后一道防线进行验证
- 不影响内部消息历史管理
- 只在实际需要时执行验证

#### 3. 保持 patched_history 纯净

**文件**: `scider/core/types.py`

**改动**: 移除了 `patched_history` 中的验证逻辑

**原因**:
- `@property` 应该是纯函数，不应有副作用（如日志）
- 避免每次访问都重新验证（性能问题）
- 验证应该在使用点进行，而不是在数据准备点

### 验证逻辑详解

```python
def validate_and_clean_messages(messages: list[dict]) -> list[dict]:
    """
    核心验证逻辑：

    1. 遍历所有消息
    2. 检测 assistant 消息是否包含 tool_calls
    3. 收集后续所有 tool responses（直到遇到非 tool 消息）
    4. 验证所有 tool_call_id 是否都有对应的 response
    5. 如果有缺失：
       - 跳过该 assistant 消息
       - 跳过所有部分 tool responses
       - 记录警告日志（包含缺失的 tool_call_ids）
    6. 如果完整：保留整个序列
    """
```

**关键改进**:
- ✅ 检查所有 tool_call_ids，而不只是检查下一条消息
- ✅ 处理多个 tool_calls 的情况
- ✅ 跳过部分 tool responses，保持序列完整性
- ✅ 提供详细的警告信息，便于调试

## 测试验证

### 单元测试

**文件**: `test_message_validation.py`

**测试用例**:
1. ✅ 有效消息序列保持不变
2. ✅ 完整的 tool_calls/responses 序列被保留
3. ✅ 缺失 tool responses 的消息被移除
4. ✅ 多个 tool_calls 全部有 responses 时保留
5. ✅ 多个 tool_calls 部分有 responses 时移除

### 端到端测试

**测试场景**: DataAgent 完整工作流

**结果**:
- ✅ 会话状态: completed
- ✅ 修复触发: 2 次
- ✅ 最终错误: 0 个
- ✅ 运行时长: ~6 分钟

## 性能影响

### 时间复杂度
- O(n) 其中 n 是消息数量
- 每条消息最多访问一次

### 空间复杂度
- O(n) 用于存储清理后的消息列表

### 实际影响
- 验证只在 LLM 调用前执行一次
- 对于典型的消息历史（< 100 条），开销可忽略不计
- 避免了 API 错误和重试，实际上提升了性能

## 最佳实践

### ✅ 做到了

1. **单一职责**: 验证逻辑独立封装
2. **DRY 原则**: 消除了代码重复
3. **可测试性**: 纯函数，完整的单元测试
4. **清晰的日志**: 包含具体的缺失 tool_call_ids
5. **性能优化**: 只在必要时验证
6. **向后兼容**: 不影响现有功能

### 🔄 可以改进

1. **根本原因**: 仍需调查为什么会出现不完整的 tool_calls/responses
2. **缓存机制**: 可以为 `patched_history` 添加缓存
3. **监控指标**: 添加 metrics 跟踪验证触发频率
4. **更好的错误处理**: 考虑是否应该抛出异常而不是静默跳过

## 部署和监控

### 部署步骤

1. 确保使用 SciDER 独立环境: `/Users/liuzf/opencode/SciDER/.venv/`
2. 重启服务: `pkill -f api_server_full.py && python api_server_full.py`
3. 验证健康检查: `curl http://localhost:8086/health`

### 监控指标

监控日志中的警告信息：
```bash
grep "Skipping assistant message with tool_calls" scider.log
```

如果频繁出现，说明存在更深层的问题需要调查。

## 总结

这次重构实现了：
- ✅ 消除代码重复
- ✅ 提高可维护性
- ✅ 增强可测试性
- ✅ 改进日志信息
- ✅ 优化性能
- ✅ 遵循最佳实践

修复已验证有效，可以投入生产使用。

---

**修复日期**: 2026-03-07
**验证状态**: ✅ 通过
**测试覆盖**: 单元测试 + 端到端测试
