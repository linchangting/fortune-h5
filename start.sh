#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/public"
RUN_DIR="$PROJECT_DIR/.run"
BACKEND_PORT=8000
FRONTEND_PORT=8080

cleanup() {
  echo "正在停止服务..."
  [ -f "$RUN_DIR/backend.pid" ] && kill "$(cat "$RUN_DIR/backend.pid")" 2>/dev/null || true
  [ -f "$RUN_DIR/frontend.pid" ] && kill "$(cat "$RUN_DIR/frontend.pid")" 2>/dev/null || true
  rm -rf "$RUN_DIR"
  echo "已停止。"
}
trap cleanup EXIT INT TERM

mkdir -p "$RUN_DIR"

if ! command -v python3 >/dev/null 2>&1; then
  echo "未找到 python3，请先安装 Python 3。"
  exit 1
fi

if [ ! -f "$BACKEND_DIR/.env" ]; then
  if [ -f "$BACKEND_DIR/.env.example" ]; then
    cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
    echo "已自动创建 backend/.env，请填入你的 DASHSCOPE_API_KEY。"
  else
    echo "未找到 .env.example"
    exit 1
  fi
fi

echo "安装后端依赖..."
python3 -m pip install -q --no-cache-dir -r "$BACKEND_DIR/requirements.txt"

if lsof -nP -iTCP:$BACKEND_PORT -sTCP:LISTEN >/dev/null 2>&1; then
  echo "后端已在端口 $BACKEND_PORT 运行，跳过。"
else
  echo "启动后端: http://localhost:$BACKEND_PORT"
  cd "$BACKEND_DIR"
  nohup python3 -m uvicorn app.main:app --reload --port "$BACKEND_PORT" \
    > "$RUN_DIR/backend.log" 2>&1 &
  echo $! > "$RUN_DIR/backend.pid"
  cd "$PROJECT_DIR"
fi

if lsof -nP -iTCP:$FRONTEND_PORT -sTCP:LISTEN >/dev/null 2>&1; then
  echo "前端已在端口 $FRONTEND_PORT 运行，跳过。"
else
  echo "启动前端: http://localhost:$FRONTEND_PORT"
  nohup python3 -m http.server "$FRONTEND_PORT" --directory "$FRONTEND_DIR" \
    > "$RUN_DIR/frontend.log" 2>&1 &
  echo $! > "$RUN_DIR/frontend.pid"
fi

echo ""
echo "========================================="
echo "  今日运势 - 八字算命 H5"
echo "========================================="
echo "  前端: http://localhost:$FRONTEND_PORT"
echo "  后端: http://localhost:$BACKEND_PORT/docs"
echo "  日志: $RUN_DIR/"
echo "========================================="
echo ""

if command -v open >/dev/null 2>&1; then
  sleep 1
  open "http://localhost:$FRONTEND_PORT" >/dev/null 2>&1 || true
fi

wait
