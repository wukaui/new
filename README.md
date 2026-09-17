# memhost

把「记忆宿主」以 HTTP 端口的形式暴露出来的服务。

**v1 目标只有一个：把端口拿住、把服务跑起来。** 现在它只有连通性端点，真正的记忆检索 / 写入、agent 任务端点还没接——那是下一版的事。

## 跑起来

```bash
python3 -m uvicorn memhost.server:app --host 0.0.0.0 --port 8900
```

依赖：`fastapi`、`uvicorn`（其余都是标准库）。

自测：

```bash
curl http://127.0.0.1:8900/health
# {"status":"ok","service":"memhost","version":"0.0.1-port-only","time":...}
```

## 端点

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | 连通性自测，任何调用方都能打 |
| GET | `/` | 列出当前可用端点 |
| POST | `/echo` | 原样回显请求体，用来验证通路 |

环境变量：

- `MEMHOST_PORT`：默认 `8900`
- `MEMHOST_TOKEN`：设了以后所有请求必须带 `Authorization: Bearer <token>`（`/health` 除外）。v1 默认不设。

## 目录

```
memhost/                       本仓库的主体：服务外壳
  server.py                    FastAPI 应用
vendor/mini-swe-agent/         上游 mini-swe-agent 源码（MIT，原样保留）
VENDORED.md                    上游来源、版本、我们的改动口径
```

## 与上游的关系

宿主内核 = [mini-swe-agent](https://github.com/SWE-agent/mini-swe-agent)（MIT，Princeton SWE-agent 团队），整份放在 `vendor/`，**一行未改**（核心 `agents/default.py` = 190 行）。本仓库的全部改动都在 `memhost/`。

## 路线图

- [ ] 记忆检索 / 写入端点
- [ ] agent 任务端点（接 `vendor/` 里的宿主循环）
- [ ] token 鉴权默认开启
- [ ] 部署脚本（开机自启 / 容器化）

## 许可

上游 `vendor/mini-swe-agent/` 为 MIT，许可见该目录下的 `LICENSE.md`。
本仓库自身的许可待定。
