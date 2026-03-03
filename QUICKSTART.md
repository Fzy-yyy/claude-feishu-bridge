# 快速入门指南

## 📦 第一步：安装依赖

```bash
# 1. 进入项目目录
cd D:\CODE\claude-feishu-bridge

# 2. 创建虚拟环境
python -m venv venv

# 3. 激活虚拟环境
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 4. 安装依赖
pip install -r requirements.txt
```

## 🔧 第二步：配置飞书应用

### 1. 创建飞书应用

访问 https://open.feishu.cn/app 创建企业自建应用

### 2. 配置权限

在「权限管理」中添加：
- ✅ `im:message` - 获取与发送单聊、群组消息
- ✅ `im:message:send_as_bot` - 以应用身份发消息

### 3. 启用事件订阅

在「事件订阅」中：
- 选择「使用 WebSocket 连接」
- 订阅事件：`im.message.receive_v1`

### 4. 获取凭证

在「凭证与基础信息」页面复制：
- App ID: `cli_xxxxx`
- App Secret: `xxxxx`

### 5. 发布应用

在「版本管理与发布」中创建版本并发布

## ⚙️ 第三步：配置项目

编辑 `config.yaml`（如果不存在，复制 `config.yaml.example`）：

```yaml
# 1. 填入飞书凭证
feishu:
  app_id: "cli_xxxxx"      # 替换为你的 App ID
  app_secret: "xxxxx"      # 替换为你的 App Secret

# 2. 配置工作目录
claude:
  allowed_work_dirs:
    - "D:/CODE/my-project"  # 替换为你的项目路径

  work_dir: "D:/CODE/my-project"  # 当前工作目录
```

**重要提示**：
- 工作目录必须是绝对路径
- Windows 使用正斜杠 `/` 或双反斜杠 `\\`
- 确保目录已存在

## 🚀 第四步：启动程序

### 方式一：使用启动脚本（推荐）

```bash
# Windows
start.bat

# Linux/Mac
chmod +x start.sh
./start.sh
```

### 方式二：直接运行

```bash
python main.py
```

## ✅ 第五步：测试

1. 在飞书中搜索你的应用名称
2. 打开与应用的对话
3. 发送测试消息：

```
你好，帮我创建一个 test.txt 文件
```

4. 如果收到权限请求，回复 `允许`

## 🎯 常用命令

在飞书中发送以下命令：

- `/help` - 查看帮助
- `/status` - 查看状态
- `/restart` - 重启会话
- `/approve_all on` - 启用自动批准

## ⚠️ 常见问题

### 问题 1：Claude CLI 未找到

**解决**：安装 Claude Code CLI
```bash
# 访问官方文档安装
https://docs.anthropic.com/claude/docs/claude-code
```

### 问题 2：工作目录验证失败

**解决**：检查 `config.yaml` 中的路径
- 使用绝对路径
- 确保目录存在
- Windows 使用 `/` 而不是 `\`

### 问题 3：飞书连接失败

**解决**：
1. 检查 app_id 和 app_secret 是否正确
2. 确认应用已发布
3. 检查网络连接

### 问题 4：依赖安装失败

**解决**：
```bash
# 升级 pip
python -m pip install --upgrade pip

# 使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## 📝 下一步

- 阅读 [README.md](README.md) 了解详细功能
- 查看 [config.yaml](config.yaml) 调整安全配置
- 查看日志文件 `logs/app.log` 排查问题

## 🎉 完成！

现在你可以在飞书中与 Claude Code 对话了！

---

**需要帮助？**
- 查看日志：`logs/app.log`
- 检查配置：`config.yaml`
- 测试命令：`/status`
