# 上游说明（vendor）

## mini-swe-agent

- 仓库：https://github.com/SWE-agent/mini-swe-agent
- 提交：`04d809ceab9df28f9adaed044884180159172930`（2026-09-03）
- 版本：2.4.6
- 许可：MIT（见 `vendor/mini-swe-agent/LICENSE.md`，随源码保留）
- 位置：`vendor/mini-swe-agent/`（整份源码，含官方 docs / tests / pyproject）

**为什么把源码放进来**：作品要在任何机器上可复现运行，且答辩时要能一行行讲清宿主循环；直接把上游源码纳入仓库，改动量（新增 vs 修改）才可核对。

**我们的改动**：全部在本仓库自己的 `memhost/` 下，**上游文件一个没动**。

| 文件 | 改动 |
|---|---|
| `memhost/server.py` | 新增：HTTP 服务外壳，把宿主能力以端口形式暴露出来（v1 只有连通性端点） |

上游核心 `vendor/mini-swe-agent/src/minisweagent/agents/default.py` = **190 行，未修改**。

核对：

```bash
grep -c '' vendor/mini-swe-agent/src/minisweagent/agents/default.py        # 190
grep -c '' $(find vendor/mini-swe-agent/src -name '*.py') | awk -F: '{s+=$2} END {print s}'   # 5349
```

> 注意：别写成 191 行。用 `grep -c ''` 数过，是 190。
