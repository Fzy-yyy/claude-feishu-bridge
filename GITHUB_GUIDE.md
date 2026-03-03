# GitHub 上传指南

本指南将帮助你将 Claude-Feishu Bridge 项目上传到 GitHub。

## 前置准备

### 1. 安装 Git

如果还没有安装 Git：

**Windows**: 下载并安装 [Git for Windows](https://git-scm.com/download/win)

**Mac**:
```bash
brew install git
```

**Linux**:
```bash
sudo apt-get install git  # Ubuntu/Debian
sudo yum install git      # CentOS/RHEL
```

### 2. 配置 Git

首次使用需要配置用户信息：

```bash
git config --global user.name "你的名字"
git config --global user.email "your.email@example.com"
```

### 3. 创建 GitHub 账号

访问 [GitHub](https://github.com) 注册账号（如果还没有）。

---

## 步骤 1: 初始化 Git 仓库

在项目目录中打开终端（Git Bash 或命令行）：

```bash
# 进入项目目录
cd d:/CODE/claude-feishu-bridge

# 初始化 Git 仓库
git init

# 查看状态
git status
```

---

## 步骤 2: 创建 .gitignore 文件

确保 `.gitignore` 文件包含以下内容（避免上传敏感信息和不必要的文件）：

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
ENV/
*.egg-info/
dist/
build/

# 敏感配置文件
config.yaml
.env

# 日志和数据
logs/
data/
*.log

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# 系统文件
.DS_Store
Thumbs.db

# Claude 相关
.claude/

# 临时文件
*.tmp
*.bak
```

---

## 步骤 3: 添加文件到 Git

```bash
# 添加所有文件（.gitignore 会自动排除不需要的文件）
git add .

# 查看将要提交的文件
git status
```

**重要**: 确认 `config.yaml` 和 `.env` 等敏感文件没有被添加！

---

## 步骤 4: 创建首次提交

```bash
git commit -m "Initial commit: Claude-Feishu Bridge project

- Add core functionality for Claude Code and Feishu integration
- Add Docker support
- Add configuration templates and documentation"
```

---

## 步骤 5: 在 GitHub 上创建仓库

### 方式 1: 通过网页创建

1. 登录 [GitHub](https://github.com)
2. 点击右上角的 `+` 号，选择 `New repository`
3. 填写仓库信息：
   - **Repository name**: `claude-feishu-bridge`
   - **Description**: `A bridge connecting Claude Code with Feishu (Lark) for seamless AI-powered collaboration`
   - **Visibility**: 选择 `Public`（公开）或 `Private`（私有）
   - **不要**勾选 "Initialize this repository with a README"（我们已经有文件了）
4. 点击 `Create repository`

### 方式 2: 使用 GitHub CLI（推荐）

如果安装了 `gh` CLI：

```bash
# 登录 GitHub
gh auth login

# 创建仓库（公开）
gh repo create claude-feishu-bridge --public --source=. --remote=origin

# 或创建私有仓库
gh repo create claude-feishu-bridge --private --source=. --remote=origin
```

---

## 步骤 6: 关联远程仓库

如果通过网页创建的仓库，需要手动关联：

```bash
# 添加远程仓库（替换 YOUR_USERNAME 为你的 GitHub 用户名）
git remote add origin https://github.com/YOUR_USERNAME/claude-feishu-bridge.git

# 验证远程仓库
git remote -v
```

---

## 步骤 7: 推送代码到 GitHub

```bash
# 推送到 main 分支（首次推送）
git push -u origin main

# 如果提示分支名是 master，可以重命名为 main
git branch -M main
git push -u origin main
```

如果遇到认证问题，可能需要：

### 使用 Personal Access Token (推荐)

1. 访问 GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. 点击 `Generate new token (classic)`
3. 选择权限：`repo`（完整仓库访问权限）
4. 生成并复制 token
5. 推送时使用 token 作为密码

### 或配置 SSH 密钥

```bash
# 生成 SSH 密钥
ssh-keygen -t ed25519 -C "your.email@example.com"

# 复制公钥
cat ~/.ssh/id_ed25519.pub

# 将公钥添加到 GitHub: Settings → SSH and GPG keys → New SSH key
```

然后修改远程仓库 URL：

```bash
git remote set-url origin git@github.com:YOUR_USERNAME/claude-feishu-bridge.git
```

---

## 步骤 8: 完善仓库信息

### 添加 README 徽章

在 `README.md` 顶部添加：

```markdown
# Claude-Feishu Bridge

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)](https://www.docker.com/)

A bridge connecting Claude Code with Feishu (Lark) for seamless AI-powered collaboration.
```

### 添加 LICENSE 文件

```bash
# 创建 MIT License（示例）
cat > LICENSE << 'EOF'
MIT License

Copyright (c) 2026 [Your Name]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
EOF

# 提交 LICENSE
git add LICENSE
git commit -m "Add MIT License"
git push
```

### 设置仓库主题和描述

在 GitHub 仓库页面：
1. 点击右上角的 ⚙️ (Settings)
2. 在 About 部分添加：
   - **Description**: `A bridge connecting Claude Code with Feishu (Lark)`
   - **Topics**: `claude`, `feishu`, `lark`, `chatbot`, `ai`, `python`, `docker`
   - **Website**: 你的项目网站（如果有）

---

## 步骤 9: 创建 Release（可选）

创建第一个版本发布：

```bash
# 创建标签
git tag -a v1.0.0 -m "Release version 1.0.0"

# 推送标签
git push origin v1.0.0
```

或使用 GitHub CLI：

```bash
gh release create v1.0.0 \
  --title "v1.0.0 - Initial Release" \
  --notes "First stable release of Claude-Feishu Bridge

Features:
- Claude Code integration
- Feishu (Lark) bot support
- Docker deployment
- Permission management
- Security controls"
```

---

## 日常使用

### 提交更改

```bash
# 查看修改
git status
git diff

# 添加文件
git add <file>

# 提交
git commit -m "描述你的更改"

# 推送
git push
```

### 拉取更新

```bash
# 拉取最新代码
git pull origin main
```

### 创建分支

```bash
# 创建并切换到新分支
git checkout -b feature/new-feature

# 推送分支
git push -u origin feature/new-feature
```

---

## 安全检查清单

在推送前，确保：

- [ ] `config.yaml` 不在仓库中（已在 .gitignore）
- [ ] `.env` 文件不在仓库中（已在 .gitignore）
- [ ] 没有硬编码的密钥或密码
- [ ] `config.yaml.example` 中的示例值已替换为占位符
- [ ] 日志文件和数据文件已排除
- [ ] 虚拟环境目录已排除

验证命令：

```bash
# 检查将要推送的文件
git ls-files

# 确认敏感文件不在列表中
git ls-files | grep -E "(config.yaml|.env)"
# 应该没有输出
```

---

## 常见问题

### Q1: 推送时要求输入用户名密码

**解决**: 使用 Personal Access Token 或配置 SSH 密钥（见步骤 7）

### Q2: 不小心提交了敏感文件

**解决**: 从历史记录中删除

```bash
# 从 Git 历史中删除文件
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch config.yaml" \
  --prune-empty --tag-name-filter cat -- --all

# 强制推送（谨慎使用）
git push origin --force --all
```

### Q3: 想要更改仓库名称

在 GitHub 仓库页面：Settings → Repository name → Rename

然后更新本地远程 URL：

```bash
git remote set-url origin https://github.com/YOUR_USERNAME/NEW_NAME.git
```

---

## 进阶功能

### 设置 GitHub Actions（CI/CD）

创建 `.github/workflows/test.yml`：

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: python -m pytest
```

### 启用 GitHub Pages（文档）

如果有文档网站，可以在 Settings → Pages 中启用。

---

## 下一步

- 邀请协作者：Settings → Collaborators
- 设置分支保护：Settings → Branches
- 配置 Webhooks：Settings → Webhooks
- 添加 Issue 模板：`.github/ISSUE_TEMPLATE/`
- 添加 PR 模板：`.github/PULL_REQUEST_TEMPLATE.md`

---

## 获取帮助

- [GitHub 文档](https://docs.github.com/)
- [Git 教程](https://git-scm.com/book/zh/v2)
- [GitHub CLI 文档](https://cli.github.com/manual/)

祝你的项目成功！🚀
