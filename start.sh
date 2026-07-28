#!/usr/bin/env bash
# Khởi động backend (Flask) — cũng serve luôn frontend static từ folder frontend/.
# Sau khi chạy, mở: http://127.0.0.1:5000
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PYTHON="${PYTHON:-python3}"

if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "❌ Không tìm thấy '$PYTHON'. Cài Python 3 rồi chạy lại."
  exit 1
fi

# Cài phụ thuộc nếu chưa có flask
if ! "$PYTHON" -c "import flask" >/dev/null 2>&1; then
  echo "📦 Đang cài phụ thuộc từ requirements.txt ..."
  "$PYTHON" -m pip install -r requirements.txt
fi

echo "🚀 Khởi động server tại http://127.0.0.1:5000  (Ctrl+C để dừng)"
exec "$PYTHON" backend/server.py
