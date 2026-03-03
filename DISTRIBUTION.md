# 项目分发指南

本文档介绍如何将 Claude-Feishu Bridge 项目打包并分发给其他人。

## 方案 1: 源码压缩包（推荐）

### Windows 用户

双击运行 `pack.bat`，会自动生成 `claude-feishu-bridge_YYYYMMDD_HHMMSS.zip`

或手动打包：
```bash
# 使用 PowerShell
Compress-Archive -Path core,utils,*.py,*.txt,*.md,*.yml,*.yaml.example,Dockerfile,.dockerignore -DestinationPath claude-feishu-bridge.zip
```

### Linux/Mac 用户

运行打包脚本：
```bash
chmod +x pack.sh
./pack.sh
```

或手动打包：
```bash
tar -czf claude-feishu-bridge.tar.gz \
  core/ utils/ \
  *.py *.txt *.md *.yml *.yaml.example \
  Dockerfile .dockerignore .gitignore \
  --exclude=venv --exclude=__pycache__ --exclude=logs --exclude=data
```

### 分发说明

将生成的压缩包发送给接收者，并告知：

1. 解压文件
2. 查看 `README.md` 了解项目说明
3. 查看 `QUICKSTART.md` 快速开始
4. 查看 `DOCKER.md` 了解 Docker 部署

---

## 方案 2: Docker 镜像（适合生产环境）

### 2.1 导出 Docker 镜像文件

```bash
# 1. 构建镜像
docker build -t claude-feishu-bridge:latest .

# 2. 导出镜像为 tar 文件
docker save -o claude-feishu-bridge.tar claude-feishu-bridge:latest

# 3. 压缩（可选，减小文件大小）
gzip claude-feishu-bridge.tar
```

接收者导入镜像：
```bash
# 解压（如果压缩了）
gunzip claude-feishu-bridge.tar.gz

# 导入镜像
docker load -i claude-feishu-bridge.tar

# 运行
docker run -d \
  --name claude-feishu-bridge \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/data:/app/data \
  claude-feishu-bridge:latest
```

### 2.2 推送到 Docker Hub（公开分发）

```bash
# 1. 登录 Docker Hub
docker login

# 2. 标记镜像
docker tag claude-feishu-bridge:latest yourusername/claude-feishu-bridge:latest

# 3. 推送镜像
docker push yourusername/claude-feishu-bridge:latest
```

接收者使用：
```bash
docker pull yourusername/claude-feishu-bridge:latest
docker run -d --name claude-feishu-bridge yourusername/claude-feishu-bridge:latest
```

### 2.3 推送到私有 Docker Registry

```bash
# 1. 标记镜像
docker tag claude-feishu-bridge:latest registry.example.com/claude-feishu-bridge:latest

# 2. 推送到私有仓库
docker push registry.example.com/claude-feishu-bridge:latest
```

---

## 方案 3: Git 仓库（推荐用于团队协作）

### 3.1 推送到 GitHub/GitLab

```bash
# 1. 初始化 Git 仓库（如果还没有）
git init

# 2. 添加远程仓库
git remote add origin https://github.com/yourusername/claude-feishu-bridge.git

# 3. 添加文件
git add .

# 4. 提交
git commit -m "Initial commit"

# 5. 推送
git push -u origin main
```

接收者克隆：
```bash
git clone https://github.com/yourusername/claude-feishu-bridge.git
cd claude-feishu-bridge
```

### 3.2 创建 Release

在 GitHub 上创建 Release，附带：
- 版本号（如 v1.0.0）
- 更新日志
- 预编译的压缩包

---

## 方案 4: 一键安装脚本

创建安装脚本，简化接收者的部署流程：

### install.sh (Linux/Mac)

```bash
#!/bin/bash
set -e

echo "=== Claude-Feishu Bridge 安装脚本 ==="

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到 Python 3"
    exit 1
fi

# 检查 Docker（可选）
if command -v docker &> /dev/null; then
    echo "✓ 检测到 Docker"
    read -p "使用 Docker 部署? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker-compose up -d
        exit 0
    fi
fi

# Python 部署
echo "使用 Python 部署..."
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

if [ ! -f config.yaml ]; then
    cp config.yaml.example config.yaml
    echo "请编辑 config.yaml 填入你的配置"
    exit 0
fi

python main.py
```

---

## 文件清单

分发时应包含的文件：

### 必需文件
- `core/` - 核心代码
- `utils/` - 工具函数
- `main.py` - 主程序
- `requirements.txt` - Python 依赖
- `config.yaml.example` - 配置模板
- `README.md` - 项目说明
- `QUICKSTART.md` - 快速开始

### Docker 相关（如果使用 Docker）
- `Dockerfile` - Docker 镜像定义
- `docker-compose.yml` - Docker Compose 配置
- `.dockerignore` - Docker 构建忽略
- `DOCKER.md` - Docker 部署文档

### 可选文件
- `start.sh` / `start.bat` - 启动脚本
- `pack.sh` / `pack.bat` - 打包脚本
- `.gitignore` - Git 忽略文件
- `LICENSE` - 开源协议

### 不应包含的文件
- `config.yaml` - 包含敏感信息
- `.env` - 环境变量（敏感）
- `venv/` - 虚拟环境
- `logs/` - 日志文件
- `data/` - 数据文件
- `__pycache__/` - Python 缓存
- `.git/` - Git 历史

---

## 接收者安装指南

创建一个简单的 `INSTALL.md` 给接收者：

```markdown
# 安装指南

## 前置要求

- Python 3.11+ 或 Docker
- Claude CLI（需要单独安装）
- 飞书应用凭证

## 快速安装

### 方式 1: Docker（推荐）

1. 安装 Docker 和 Docker Compose
2. 复制配置文件: `cp config.yaml.example config.yaml`
3. 编辑 `config.yaml` 填入你的飞书凭证
4. 启动: `docker-compose up -d`

### 方式 2: Python

1. 安装依赖: `pip install -r requirements.txt`
2. 复制配置文件: `cp config.yaml.example config.yaml`
3. 编辑 `config.yaml` 填入你的飞书凭证
4. 运行: `python main.py`

## 详细文档

- [README.md](README.md) - 项目介绍
- [QUICKSTART.md](QUICKSTART.md) - 快速开始
- [DOCKER.md](DOCKER.md) - Docker 部署
```

---

## 最佳实践

1. **版本管理**: 使用语义化版本号（如 v1.0.0）
2. **更新日志**: 维护 CHANGELOG.md 记录变更
3. **文档完善**: 确保 README 和安装文档清晰
4. **安全检查**: 不要包含敏感信息
5. **测试验证**: 在干净环境测试安装流程
6. **依赖锁定**: 使用 `pip freeze` 锁定依赖版本

## 推荐分发方式

| 场景 | 推荐方式 | 优点 |
|------|---------|------|
| 个人使用 | 源码压缩包 | 简单直接 |
| 团队协作 | Git 仓库 | 版本控制、协作方便 |
| 生产部署 | Docker 镜像 | 环境一致、部署简单 |
| 公开分发 | GitHub Release | 版本管理、下载方便 |
