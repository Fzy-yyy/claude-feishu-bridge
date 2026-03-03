# Claude-Feishu Bridge

将本地 Claude Code 连接到飞书，实现双向实时对话。

## ✨ 特性

- 🔐 **安全控制**: 工作目录白名单、命令过滤、路径检查
- 🚀 **实时交互**: WebSocket 长连接，无需公网 IP
- 🎯 **权限管理**: 支持工具调用权限确认
- 📝 **审计日志**: 记录所有操作，便于追溯
- 🔄 **会话管理**: 支持会话恢复和持久化

## 📋 前置条件

1. **Python 3.8+**
2. **Claude Code CLI**: [安装指南](https://docs.anthropic.com/claude/docs/claude-code)
3. **飞书应用**: 需要创建飞书企业自建应用

## 🚀 快速开始

### 1. 安装依赖

```bash
cd D:\CODE\claude-feishu-bridge
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

pip install -r requirements.txt
```

### 2. 配置飞书应用

#### 2.1 创建应用

1. 访问 [飞书开放平台](https://open.feishu.cn/app)
2. 点击「创建企业自建应用」
3. 填写应用名称和描述

#### 2.2 获取凭证

在「凭证与基础信息」页面获取：
- **App ID**: `cli_xxxxx`
- **App Secret**: `xxxxx`

#### 2.3 配置权限

在「权限管理」中添加以下权限：
- `im:message` - 获取与发送单聊、群组消息
- `im:message:send_as_bot` - 以应用身份发消息

#### 2.4 启用事件订阅

在「事件订阅」中：
1. 选择「使用 WebSocket 连接」
2. 订阅事件：`im.message.receive_v1`（接收消息）

#### 2.5 发布应用

在「版本管理与发布」中创建版本并发布到企业内部。

### 3. 配置项目

编辑 `config.yaml`:

```yaml
# 飞书配置
feishu:
  app_id: "cli_xxxxx"  # 替换为你的 App ID
  app_secret: "xxxxx"  # 替换为你的 App Secret

# Claude Code 配置
claude:
  # 允许的工作目录白名单
  allowed_work_dirs:
    - "D:/CODE/my-project"  # 替换为你的项目路径

  # 当前工作目录
  work_dir: "D:/CODE/my-project"  # 替换为你的项目路径

  # 权限模式
  permission_mode: "default"  # default | acceptEdits | plan | bypassPermissions

# 安全配置（可选调整）
security:
  enable_workdir_check: true
  audit_log: true
```

### 4. 运行程序

```bash
python main.py
```

看到以下输出表示启动成功：

```
✓ 配置文件加载成功: config.yaml
✓ 工作目录验证通过: D:/CODE/my-project
✓ Claude Code 进程已启动
✓ 飞书 WebSocket 客户端启动中...
```

### 5. 使用

1. 在飞书中搜索你的应用名称
2. 打开与应用的对话
3. 发送消息，例如：`帮我创建一个 hello.py 文件`

## 📖 使用指南

### 基本对话

直接发送消息给飞书机器人，Claude 会处理并回复：

```
你: 帮我分析一下 main.py 的代码结构
Claude: 我来帮你分析 main.py...
```

### 权限确认

当 Claude 需要执行操作时，会请求权限：

```
🔐 权限请求

工具: Bash
操作: ls -la

请回复：
• 允许 或 allow - 批准此操作
• 拒绝 或 deny - 拒绝此操作
• 允许所有 或 allow all - 本次会话自动批准所有后续请求
```

回复 `允许` 即可批准操作。

### 特殊命令

- `/help` - 显示帮助信息
- `/status` - 查看系统状态
- `/restart` - 重启 Claude 会话
- `/stop` - 停止 Claude 会话
- `/approve_all on` - 启用自动批准模式
- `/approve_all off` - 禁用自动批准模式

## 🔒 安全特性

### 1. 工作目录白名单

只允许 Claude 访问配置中指定的目录：

```yaml
claude:
  allowed_work_dirs:
    - "D:/CODE/project1"
    - "D:/CODE/project2"
```

### 2. 命令过滤

自动拦截危险命令：

```yaml
security:
  forbidden_commands:
    - "rm -rf /"
    - "format"
    - "del /f /s /q C:\\"
```

### 3. 路径保护

禁止访问敏感文件：

```yaml
security:
  forbidden_paths:
    - "*.key"
    - "*.pem"
    - "C:/Windows/System32/*"
```

### 4. 审计日志

所有操作都会记录到日志文件：

```
[AUDIT] Bash命令 {"command": "ls -la", "tool": "Bash"}
[AUDIT] Read文件 {"path": "main.py", "tool": "Read"}
```

## 🛠️ 配置说明

### 权限模式

- `default`: 每次工具调用都需要确认（推荐）
- `acceptEdits`: 文件编辑自动通过，其他需要确认
- `plan`: 只做规划不执行，审批后再执行
- `bypassPermissions`: 全部自动通过（谨慎使用）

### 预授权工具

可以预先授权某些工具，无需每次确认：

```yaml
claude:
  allowed_tools:
    - "Read"    # 读取文件
    - "Grep"    # 搜索内容
    - "Glob"    # 搜索文件
```

## 📝 日志

日志文件位置：`logs/app.log`

查看实时日志：

```bash
tail -f logs/app.log  # Linux/Mac
Get-Content logs/app.log -Wait  # Windows PowerShell
```

## ❓ 常见问题

### 1. Claude CLI 未找到

**错误**: `✗ Claude CLI 未找到`

**解决**: 安装 Claude Code CLI

```bash
# 参考官方文档安装
# https://docs.anthropic.com/claude/docs/claude-code
```

### 2. 工作目录验证失败

**错误**: `✗ 工作目录不在白名单中`

**解决**: 在 `config.yaml` 中添加目录到 `allowed_work_dirs`

### 3. 飞书连接失败

**错误**: 飞书 WebSocket 连接失败

**解决**:
1. 检查 `app_id` 和 `app_secret` 是否正确
2. 确认应用已发布
3. 检查网络连接

### 4. 权限请求无响应

**问题**: 回复"允许"后没有反应

**解决**: 确保回复的是纯文本 `允许` 或 `allow`，不要有其他内容

## 🔧 开发

### 项目结构

```
claude-feishu-bridge/
├── main.py                  # 主程序
├── config.yaml              # 配置文件
├── requirements.txt         # 依赖列表
├── core/                    # 核心模块
│   ├── security.py          # 安全控制
│   ├── claude_agent.py      # Claude 交互
│   ├── feishu_client.py     # 飞书客户端
│   └── message_router.py    # 消息路由
├── utils/                   # 工具模块
│   └── logger.py            # 日志工具
├── logs/                    # 日志目录
└── data/                    # 数据目录
```

### 扩展功能

可以在 `message_router.py` 中添加自定义命令：

```python
async def _handle_command(self, message_id: str, command: str):
    if command == "/my_command":
        # 自定义逻辑
        await self.feishu.reply_text(message_id, "执行自定义命令")
```

## 📄 许可证

MIT License

## 🙏 致谢

- [Claude Code](https://docs.anthropic.com/claude/docs/claude-code) - Anthropic
- [飞书开放平台](https://open.feishu.cn/) - 字节跳动
- [cc-connect](https://github.com/chenhg5/cc-connect) - 参考项目

## 📮 反馈

如有问题或建议，欢迎提交 Issue。
