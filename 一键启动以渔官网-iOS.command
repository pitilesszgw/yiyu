#!/bin/zsh
set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$ROOT_DIR/.yiyu_ios_venv"
PORT=5001
LOG_FILE="$ROOT_DIR/yiyu_ios_start.log"

cd "$ROOT_DIR"

get_lan_ip() {
    ipconfig getifaddr en0 2>/dev/null \
        || ipconfig getifaddr en1 2>/dev/null \
        || python3 - <<'PY'
import socket

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
try:
    s.connect(("8.8.8.8", 80))
    print(s.getsockname()[0])
finally:
    s.close()
PY
}

LAN_IP="$(get_lan_ip)"
LOCAL_URL="http://127.0.0.1:$PORT"
IOS_URL="http://$LAN_IP:$PORT"

echo "========================================================"
echo "        以渔官网 iOS 一键启动"
echo "========================================================"
echo ""

if ! command -v python3 >/dev/null 2>&1; then
    echo "没有找到 Python 3，请先安装 Python 3 后再运行。"
    read -r "?按回车关闭窗口..."
    exit 1
fi

if [ ! -d "$VENV_DIR" ]; then
    echo "首次运行：正在准备独立运行环境..."
    python3 -m venv "$VENV_DIR"
fi

echo "正在检查运行依赖..."
"$VENV_DIR/bin/python" -m pip install --upgrade pip >/dev/null
"$VENV_DIR/bin/python" -m pip install -r "$ROOT_DIR/requirements.txt" >/dev/null

if lsof -nP -iTCP:$PORT -sTCP:LISTEN >/dev/null 2>&1; then
    echo "服务已经在运行，直接打开官网。"
else
    echo "正在启动官网服务..."
    "$VENV_DIR/bin/python" app.py > "$LOG_FILE" 2>&1 &
fi

echo "等待服务就绪..."
for i in {1..30}; do
    if curl -fsS "$LOCAL_URL" >/dev/null 2>&1; then
        break
    fi
    sleep 1
done

if ! curl -fsS "$LOCAL_URL" >/dev/null 2>&1; then
    echo "启动失败，请查看日志：$LOG_FILE"
    read -r "?按回车关闭窗口..."
    exit 1
fi

open "$LOCAL_URL"

echo ""
echo "已启动。"
echo ""
echo "这台 Mac 打开："
echo "  $LOCAL_URL"
echo ""
echo "iPhone/iPad 打开："
echo "  $IOS_URL"
echo ""
echo "iOS 一键入口设置："
echo "  1. 确保 iPhone/iPad 和这台 Mac 在同一个 Wi-Fi"
echo "  2. 用 Safari 打开上面的 iPhone/iPad 链接"
echo "  3. 点分享按钮，选择「添加到主屏幕」"
echo "  4. 名称填「以渔官网」，以后桌面点一下就能打开"
echo ""
echo "服务正在后台运行。要停止它，可关闭占用 $PORT 端口的 Python 进程，或重启电脑。"
echo "日志文件：$LOG_FILE"
echo ""
read -r "?按回车关闭窗口..."
