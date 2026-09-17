"""memhost —— 记忆宿主服务的端口骨架（占位版）。

目的：先把端口拿住、把连通性打通，方便队友对接和后续修改。
现在只有三个端点，真正的记忆/agent 逻辑等接口定下来再往这里加。

跑：
    python3 -m uvicorn memhost.server:app --host 0.0.0.0 --port 8900

环境变量：
    MEMHOST_PORT    默认 8900
    MEMHOST_TOKEN   如果设置，所有请求必须带 `Authorization: Bearer <token>`
"""

from __future__ import annotations

import os
import time

from fastapi import FastAPI, Header, HTTPException, Request

PORT = int(os.getenv("MEMHOST_PORT", "8900"))
TOKEN = os.getenv("MEMHOST_TOKEN", "")
SERVICE = "memhost"
VERSION = "0.0.1-port-only"

app = FastAPI(title=SERVICE, version=VERSION, description="记忆宿主服务骨架（占位）")


@app.middleware("http")
async def _require_token(request: Request, call_next):
    """MEMHOST_TOKEN 为空时不校验（本地自测用）；设了就强制带 token。"""
    if TOKEN and request.url.path != "/health":
        if request.headers.get("authorization") != f"Bearer {TOKEN}":
            raise HTTPException(status_code=401, detail="missing or bad token")
    return await call_next(request)


@app.get("/health")
def health() -> dict:
    """队友连通性自测用。"""
    return {"status": "ok", "service": SERVICE, "version": VERSION, "time": time.time()}


@app.get("/")
def index() -> dict:
    return {
        "service": SERVICE,
        "version": VERSION,
        "port": PORT,
        "endpoints": {"GET /health": "连通性自测", "POST /echo": "原样回显，测通路"},
        "todo": ["记忆检索/写入端点", "agent 任务端点"],
    }


@app.post("/echo")
async def echo(request: Request, authorization: str | None = Header(default=None)) -> dict:
    body = await request.body()
    return {"echo": body.decode("utf-8", errors="replace"), "auth_seen": bool(authorization)}
