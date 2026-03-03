# 问题修复总结

## 问题描述
Claude Code 启动后无法正常响应用户消息。

## 根本原因

发现了 3 个关键问题：

### 1. 嵌套会话检测
**问题**: Claude CLI 检测到 `CLAUDECODE` 环境变量，拒绝启动（防止嵌套会话）
**错误**: `Error: Claude Code cannot be launched inside another Claude Code session.`
**解决**: 在启动子进程前删除 `CLAUDECODE` 环境变量

### 2. Git Bash 路径
**问题**: Windows 上 Claude Code 需要 git-bash，但找不到路径
**错误**: `Claude Code on Windows requires git-bash`
**解决**:
- 使用 `shutil.which('bash.exe')` 自动查找
- 设置 `CLAUDE_CODE_GIT_BASH_PATH` 环境变量

### 3. 命令行参数
**问题**: 缺少 `--print` 参数和消息格式错误
**错误**:
- `When using --print, --output-format=stream-json requires --verbose`
- `Expected message role 'user', got 'undefined'`
**解决**:
- 添加 `--print` 参数
- 消息格式中添加 `role: "user"` 字段

## 修复内容

### core/claude_agent.py

1. **环境变量处理**:
```python
# 移除 CLAUDECODE 避免嵌套检测
env = os.environ.copy()
if 'CLAUDECODE' in env:
    del env['CLAUDECODE']

# 自动查找并设置 git-bash 路径
bash_exe = shutil.which('bash.exe')
if bash_exe:
    env['CLAUDE_CODE_GIT_BASH_PATH'] = bash_exe
```

2. **命令参数**:
```python
args = [
    claude_path,
    "--print",  # 新增：必须加这个参数
    "--output-format", "stream-json",
    "--verbose",
    "--input-format", "stream-json",
    "--permission-prompt-tool", "stdio",
]
```

3. **消息格式**:
```python
message = {
    "type": "user",
    "message": {
        "role": "user",  # 新增：必须包含 role 字段
        "content": content
    }
}
```

4. **错误监控**:
- 添加进程启动后的状态检查
- 添加 stderr 监控任务
- 改进错误日志输出

## 测试结果

✅ Claude CLI 成功启动
✅ 成功发送消息
✅ 成功接收响应
✅ 正确解析 JSON 事件流

示例响应：
```json
{
  "type": "assistant",
  "message": {
    "content": [{
      "text": "Hey! I'm Kiro, ready to help with your coding tasks. What are you working on?",
      "type": "text"
    }]
  }
}
```

## 下一步

现在可以正常使用了！重启主程序即可：

```bash
cd D:\CODE\claude-feishu-bridge
python main.py
```

然后在飞书中发送消息测试。
