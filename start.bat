@echo off
chcp 65001 >nul
echo ========================================
echo Claude-Feishu Bridge 启动脚本
echo ========================================
echo.

REM 检查虚拟环境
if not exist "venv\Scripts\activate.bat" (
    echo [错误] 虚拟环境不存在
    echo 请先运行: python -m venv venv
    pause
    exit /b 1
)

REM 激活虚拟环境
call venv\Scripts\activate.bat

REM 检查配置文件
if not exist "config.yaml" (
    echo [警告] config.yaml 不存在
    echo 正在从示例文件复制...
    copy config.yaml.example config.yaml
    echo.
    echo [重要] 请编辑 config.yaml 填入你的配置
    echo 1. 飞书 app_id 和 app_secret
    echo 2. 工作目录路径
    echo.
    pause
    exit /b 1
)

REM 启动程序
echo [启动] 正在启动 Claude-Feishu Bridge...
echo.
python main.py

REM 如果程序异常退出，暂停以查看错误
if errorlevel 1 (
    echo.
    echo [错误] 程序异常退出
    pause
)
