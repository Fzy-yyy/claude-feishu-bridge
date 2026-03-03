# Docker 部署指南

## 快速开始

### 1. 准备配置文件

复制配置文件模板并修改：

```bash
cp config.yaml.example config.yaml
```

编辑 `config.yaml`，填入你的飞书应用凭证和其他配置。

### 2. 构建镜像

```bash
docker build -t claude-feishu-bridge .
```

### 3. 运行容器

#### 使用 Docker 命令

```bash
docker run -d \
  --name claude-feishu-bridge \
  --restart unless-stopped \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/work:/app/work \
  claude-feishu-bridge
```

#### 使用 Docker Compose（推荐）

```bash
docker-compose up -d
```

### 4. 查看日志

```bash
# 使用 Docker 命令
docker logs -f claude-feishu-bridge

# 使用 Docker Compose
docker-compose logs -f
```

### 5. 停止服务

```bash
# 使用 Docker 命令
docker stop claude-feishu-bridge

# 使用 Docker Compose
docker-compose down
```

## 目录结构

```
claude-feishu-bridge/
├── Dockerfile              # Docker 镜像定义
├── docker-compose.yml      # Docker Compose 配置
├── .dockerignore          # Docker 构建忽略文件
├── config.yaml            # 配置文件（需要创建）
├── logs/                  # 日志目录（自动创建）
├── data/                  # 数据目录（自动创建）
└── work/                  # Claude 工作目录（自动创建）
```

## 配置说明

### 环境变量

可以通过环境变量覆盖配置文件中的某些设置：

```yaml
environment:
  - PYTHONUNBUFFERED=1
  - CLAUDE_CODE_GIT_BASH_PATH=/usr/bin/bash
```

### 数据持久化

以下目录需要挂载到宿主机以保持数据持久化：

- `config.yaml`: 配置文件（只读）
- `logs/`: 日志文件
- `data/`: 会话数据
- `work/`: Claude 工作目录

## 注意事项

### Claude CLI 安装

Dockerfile 中包含了 Claude CLI 的安装步骤。如果官方安装脚本不可用，你需要：

1. 手动下载 Claude CLI 二进制文件
2. 修改 Dockerfile，将二进制文件复制到镜像中
3. 确保 Claude CLI 在 PATH 中可用

示例：

```dockerfile
# 方式 1: 从本地复制
COPY claude /usr/local/bin/claude
RUN chmod +x /usr/local/bin/claude

# 方式 2: 从 URL 下载
RUN curl -L https://example.com/claude -o /usr/local/bin/claude \
    && chmod +x /usr/local/bin/claude
```

### 权限问题

如果遇到权限问题，可以在 Dockerfile 中添加：

```dockerfile
# 创建非 root 用户
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser
```

### 网络配置

如果需要访问外部服务，确保容器有正确的网络配置：

```yaml
networks:
  - default

networks:
  default:
    driver: bridge
```

## 故障排查

### 查看容器状态

```bash
docker ps -a | grep claude-feishu-bridge
```

### 进入容器调试

```bash
docker exec -it claude-feishu-bridge bash
```

### 检查 Claude CLI

```bash
docker exec -it claude-feishu-bridge claude --version
```

### 重新构建镜像

```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## 生产环境建议

1. **使用环境变量管理敏感信息**：不要将敏感信息直接写入配置文件
2. **配置日志轮转**：避免日志文件过大
3. **设置资源限制**：

```yaml
services:
  claude-feishu-bridge:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

4. **配置健康检查**：确保服务正常运行
5. **使用 Docker secrets**：管理敏感配置

## 更新部署

```bash
# 拉取最新代码
git pull

# 重新构建并启动
docker-compose up -d --build
```
