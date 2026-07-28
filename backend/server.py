"""
Flask backend cho ReAct Agent UI (folder riêng `backend/`).

Serve static từ `frontend/`, JSON API cho test cases, và SSE stream cho ReAct log.
Chạy: python backend/server.py  ->  http://127.0.0.1:5000
"""

from __future__ import annotations

import json
import os
import sys

from flask import Flask, Response, jsonify, send_from_directory

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "src"))

from app import get_llm_provider, iter_react_agent, load_test_cases  # noqa: E402

FRONTEND_DIR = os.path.join(REPO_ROOT, "frontend")

app = Flask(__name__, static_folder=None)

provider = get_llm_provider()
model_name = getattr(provider, "model_name", "Offline Mock Mode")
print(
    f"🔌 LLM Provider đang hoạt động: {provider.__class__.__name__} "
    f"(Model: {model_name})"
)


@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/<path:filename>")
def static_files(filename: str):
    return send_from_directory(FRONTEND_DIR, filename)


@app.route("/api/test_cases")
def test_cases():
    return jsonify(load_test_cases())


@app.route("/api/provider")
def provider_info():
    return jsonify(
        {
            "provider": provider.__class__.__name__,
            "model": model_name,
        }
    )


@app.route("/api/agent/stream")
def agent_stream():
    from flask import request

    query = (request.args.get("query") or "").strip()
    if not query:
        return jsonify({"status": "error", "message": "Thiếu tham số query."}), 400

    def event_stream():
        try:
            for event in iter_react_agent(query, provider):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as exc:  # defensive: không làm rớt kết nối SSE
            err = {"type": "error", "message": f"{exc}"}
            yield f"data: {json.dumps(err, ensure_ascii=False)}\n\n"

    return Response(
        event_stream(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, threaded=True, debug=False)
