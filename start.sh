#!/bin/bash

echo "========================================"
echo "Claude-Feishu Bridge 启动脚本"
echo "========================================"
echo ""

# 检查虚拟环境
if [ ! -f "venv/bin/activate" ]; then
    echo "[错误] 虚拟环境不存在"
    echo "请先运行: python -m venv venv"
    exit 1
fi

# 激活虚拟环境
source venv/bin/activate

# 检查配置文件
if [ ! -f "config.yaml" ]; then
    echo "[警告] config.yaml 不存在"
    echo "正在从示例文件复制..."
    cp config.yaml.example config.yaml
    echo ""
    echo "[重要] 请编辑 config.yaml 填入你的配置"
    echo "1. 飞书 app_id 和 app_secret"
    echo "2. 工作目录路径"
    echo ""
    exit 1
fi

# 启动程序
echo "[启动] 正在启动 Claude-Feishu Bridge..."
echo ""
python main.py
