# 多轮对话问题修复

## 问题描述

1. **只能进行一次对话**：第一次对话后，Claude Code 进程被标记为未运行，第二次对话失败
2. **Claude 返回内容前包含多个空行**：影响用户体验

## 根本原因

### 问题 1: 进程状态管理错误

**位置**: `core/claude_agent.py` 的 `read_events()` 方法

**原因**:
```python
finally:
    self._running = False  # ❌ 无条件设置为 False
```

在 `read_events()` 方法的 finally 块中，无论什么原因退出循环都会将 `self._running` 设置为 False。当 `_process_claude_events()` 处理完一轮对话（收到 TURN_COMPLETE 事件）后会 break，导致：
1. `read_events()` 的 async for 循环结束
2. finally 块执行，`_running` 被设置为 False
3. 进程被标记为"未运行"
4. 第二次对话时检查 `is_alive()` 返回 False

**影响**:
- 每次对话后进程都被标记为停止
- 无法进行多轮对话
- 需要重新启动进程

### 问题 2: 空行处理和日志不足

**位置**: `core/claude_agent.py` 的 `read_events()` 方法

**原因**:
```python
line = line.strip()
if not line:
    continue  # 跳过空行但没有日志
```

- 空行被静默跳过，没有日志记录
- 缺少详细的事件解析日志
- 难以追踪问题

## 修复方案

### 修复 1: 正确管理进程状态

**修改**: `core/claude_agent.py` 的 `read_events()` 方法

**关键改动**:
```python
# 移除 finally 块中的无条件设置
# finally:
#     self._running = False  # ❌ 删除

# 只在进程真正退出时设置
if not line:
    if self.process.poll() is not None:
        logger.error(f"Claude 进程已退出，退出码: {self.process.returncode}")
        self._running = False  # ✓ 只在进程退出时设置
        # ...
    break

# 在异常时也设置
except Exception as e:
    logger.error(f"读取事件流失败: {e}", exc_info=True)
    yield ClaudeEvent(EventType.ERROR, str(e))
    self._running = False  # ✓ 异常时设置
```

**效果**:
- 进程在处理完一轮对话后仍然保持运行状态
- 可以继续接收和处理新的消息
- 支持多轮对话

### 修复 2: 增强日志和调试能力

**修改 1**: `core/claude_agent.py` 的 `read_events()` 方法
```python
# 添加详细日志
line = line.strip()
if not line:
    logger.debug("跳过空行")  # ✓ 记录空行
    continue

logger.debug(f"收到 Claude 输出: {line[:200]}...")  # ✓ 记录原始输出

try:
    data = json.loads(line)
    event = self._parse_event(data)
    if event:
        logger.debug(f"解析事件: {event.type.value}")  # ✓ 记录事件类型
        yield event
```

**修改 2**: `core/claude_agent.py` 的 `_parse_event()` 方法
```python
def _parse_event(self, data: dict) -> Optional[ClaudeEvent]:
    event_type = data.get("type")
    logger.debug(f"解析事件类型: {event_type}, 数据: {str(data)[:200]}")  # ✓ 详细日志

    if event_type == "assistant":
        message = data.get("message", {})
        content_arr = message.get("content", [])
        logger.debug(f"助手消息内容数组长度: {len(content_arr)}")  # ✓ 内容数量

        for item in content_arr:
            item_type = item.get("type")
            logger.debug(f"内容项类型: {item_type}")  # ✓ 内容类型

            if item_type == "text":
                text = item.get("text", "")
                if text:
                    logger.debug(f"文本内容: {text[:100]}")  # ✓ 文本预览
                    return ClaudeEvent(EventType.TEXT, text)
    # ...
```

**修改 3**: `config.yaml` 临时启用 DEBUG 日志
```yaml
logging:
  level: "DEBUG"  # 从 INFO 改为 DEBUG
```

**效果**:
- 可以看到每一行 Claude 输出
- 可以追踪事件解析过程
- 可以发现空行的来源
- 便于排查问题

## 测试方法

### 方法 1: 使用测试脚本

```bash
cd D:\CODE\claude-feishu-bridge
python test_multi_turn.py
```

测试脚本会：
1. 启动 Claude Code 会话
2. 发送第一条消息："你好"
3. 检查进程状态
4. 发送第二条消息："你是什么模型"
5. 检查进程状态
6. 验证多轮对话是否成功

### 方法 2: 使用飞书测试

```bash
cd D:\CODE\claude-feishu-bridge
python main.py
```

在飞书中：
1. 发送第一条消息："你好"
2. 等待回复
3. 发送第二条消息："你是什么模型"
4. 验证是否正常回复

### 方法 3: 查看日志

```bash
# 实时查看日志
tail -f logs/app.log

# 或在 Windows PowerShell 中
Get-Content logs/app.log -Wait
```

关键日志标记：
- `✓ Claude Code 进程已启动` - 进程启动
- `会话已创建: xxx` - 会话创建
- `解析事件类型: xxx` - 事件解析
- `回合完成: xxx` - 对话完成
- `进程状态: 运行中` - 进程仍在运行

## 预期结果

### 成功标志

1. **多轮对话成功**:
   ```
   第一轮对话完成
   进程状态: 运行中  ✓
   第二轮对话完成
   进程状态: 运行中  ✓
   ```

2. **日志正常**:
   ```
   收到 Claude 输出: {"type":"system","session_id":"xxx"}
   解析事件类型: system
   会话已创建: xxx
   收到 Claude 输出: {"type":"assistant","message":...}
   解析事件类型: assistant
   文本内容: Hey! I'm Kiro...
   回合完成: success
   ```

3. **无错误**:
   - 没有 "Claude Code 进程未运行" 错误
   - 没有 "进程输出流已关闭" 警告
   - 没有编码错误

### 失败标志

1. **进程退出**:
   ```
   Claude 进程已退出，退出码: 0  ✗
   Claude Code 进程未运行  ✗
   ```

2. **空输出**:
   ```
   Claude 进程输出流暂时无数据  ⚠️
   ```

3. **编码错误**:
   ```
   'gbk' codec can't decode byte 0x80  ✗
   ```

## 后续优化

1. **恢复日志级别**: 测试完成后将 `config.yaml` 中的日志级别改回 INFO
   ```yaml
   logging:
     level: "INFO"
   ```

2. **添加心跳检测**: 定期检查进程是否真的存活

3. **添加超时机制**: 如果长时间没有响应，自动重启进程

4. **优化空行处理**: 分析空行的来源，看是否可以优化

## 相关文件

- `core/claude_agent.py` - 主要修复文件
- `core/message_router.py` - 事件处理逻辑
- `config.yaml` - 日志配置
- `test_multi_turn.py` - 测试脚本
- `logs/app.log` - 运行日志

## 总结

通过正确管理 `_running` 标志和增强日志记录，成功修复了多轮对话问题。现在 Claude Code 进程可以在多轮对话中保持运行状态，支持连续的交互。
