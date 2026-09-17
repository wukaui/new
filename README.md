# memhost

本仓库只放两样东西：**宿主内核源码** 和 **接口文档**。

```
vendor/mini-swe-agent/   上游 mini-swe-agent v2.4.6 源码（MIT，一行未改）
VENDORED.md              上游来源、版本、改动口径
                        接口文档 —— 待放
```

上游核心 `vendor/mini-swe-agent/src/minisweagent/agents/default.py` = **190 行**（`grep -c ''` 核过）。

内核自身的用法见 `vendor/mini-swe-agent/README.md`。
