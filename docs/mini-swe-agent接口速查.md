# mini-swe-agent 接口速查（v2.4.6）

> 实查 2026-09-17，源码直读（`SWE-agent/mini-swe-agent`，MIT，commit `04d809ceab9df28f9adaed044884180159172930` / 2026-09-03，版本 2.4.6）。**结论放前：它的核心里留着官方指定的挂载点，我们只需写两个类，核心 190 行一行不改。**

行数核对方式（别写错，答辩会被抓）：`grep -c '' src/minisweagent/agents/default.py` → 190。

## 一、三个 Protocol（鸭子类型，**不必继承**）

```python
class Model(Protocol):                                    # __init__.py:43
    config: Any
    def query(self, messages: list[dict], **kwargs) -> dict          # 调模型，返回 message dict
    def format_message(self, **kwargs) -> dict                        # 造消息
    def format_observation_messages(self, message, outputs, template_vars=None) -> list[dict]
    def get_template_vars(self, **kwargs) -> dict
    def serialize(self) -> dict

class Environment(Protocol):                              # __init__.py:61
    config: Any
    def execute(self, action: dict, cwd: str = "") -> dict            # 执行一个动作，返回结果
    def get_template_vars(self, **kwargs) -> dict
    def serialize(self) -> dict

class Agent(Protocol):                                    # __init__.py:73
    config: Any
    def run(self, task: str, **kwargs) -> dict                        # 跑到结束，返回 exit_status/submission
    def save(self, path: Path | None, *extra_dicts) -> dict
```

### 1.1 返回值契约（照抄就没坑）

Protocol **运行时不检查**：少实现一个方法不会立刻报错，会跑到那一步才炸。所以要么照签名写，要么直接继承上游类。

**`Model.query(messages) -> 一条 assistant 消息 dict`**，关键是 `extra`：

```python
{
  "role": "assistant",
  "content": "给用户看/思考的文本，可为空",
  "extra": {
    "actions": [{"command": "..."}],   # ★ 循环据此执行；空列表 = 这步没动作
    "cost": 0.0012,                     # ★ 记账用，累加进 agent.cost
    "timestamp": 1768000000.0,
    "response": {...},                  # 原始响应，调试/trajectory 用，可选
  },
}
```

toolcall 模式下每条 action 还要带 `tool_call_id`，否则回填工具结果时对不上号（`actions_toolcall.py:75`）。

**`Model.format_observation_messages(message, outputs, template_vars) -> list[dict]`**
把 `env.execute()` 的返回渲染成回填消息。toolcall 模式：`role="tool"` + 同一个 `tool_call_id`；文本模式：`role="user"`。

**`Environment.execute(action, cwd) -> dict`**，三个键必须齐：

```python
{"output": "stdout/stderr 合并后的文本",
 "returncode": 0,          # 失败给非 0，异常给 -1
 "exception_info": ""}     # 有值会被渲染进观测里，告诉模型出事了
```

**`Agent.run(task, **kwargs) -> dict`**：返回最后一条 `role="exit"` 消息的 `extra`，即 `{"exit_status": ..., "submission": ...}`。

## 二、装配方式：查表 + **可以填全路径**

| 位置 | 机制 | 内置 |
|---|---|---|
| `models/__init__.py` → `get_model_class()` | 按名字解析类，可填 `包.类` 全路径 | litellm / openrouter / portkey / requesty（各带 `_response_model`、`_textbased_model` 变体） |
| `environments/__init__.py` → `_ENVIRONMENT_MAPPING` | 同上，可填全路径 | local / docker / singularity / bubblewrap / contree / swerex_docker / swerex_modal |
| `agents/__init__.py` → `_AGENT_MAPPING` | 同上，可填全路径 | default / interactive |

→ **我们的类用全路径挂进去就行，不动它核心里一行代码。**

模型侧：`litellm_model.py` = 任意 **OpenAI 兼容端点**（我们的 opencode-go / DeepSeek 直接接）。
全局限额（环境变量）：`MSWEA_GLOBAL_COST_LIMIT`、`MSWEA_GLOBAL_CALL_LIMIT`。

### 2.1 配置注入：每个类都能换自己的配置类

所有核心类的构造签名都是 `__init__(self, *, config_class: type = XxxConfig, **kwargs)`（`default.py:39`、`litellm_model.py:59`、`local.py:20`）。配置项用 pydantic `BaseModel` 声明，**加字段 = 继承配置类**：

```python
class MyConfig(AgentConfig):
    recall_k: int = 4

class MyAgent(DefaultAgent):
    def __init__(self, *a, **kw):
        super().__init__(*a, config_class=MyConfig, **kw)
```

配置层三件套：

- `config/*.yaml` 递归 merge，`UNSET` 哨兵跳过（`utils/serialize.py:3,6`）
- CLI 任意深度覆盖：`-c mini.yaml -c model.model_kwargs.temperature=0.5`（`config/__init__.py:31`）
- 模板变量是**三方合并**（`default.py:52`）：agent config + env 的模板变量 + model 的，再加上运行时 `n_model_calls` / `model_cost` / `elapsed_seconds`。模板用 Jinja2 + `StrictUndefined`——写错变量名立刻报错，不会静默变空串。

> 对我们的意义：换 prompt、换模型、换限额**全在 yaml 里**，代码一行不动。

### 2.2 入口与环境变量

| 命令 | 实现 | 作用 |
|---|---|---|
| `mini` / `mini-swe-agent` | `run/mini.py:main` | 本地跑一次（默认 interactive agent + local env） |
| `mini-extra config` | `run/utilities/config.py` | 管理全局 `.env` |
| `mini-extra inspect` | `run/utilities/inspector.py` | trajectory 浏览器（Textual TUI） |
| `python -m minisweagent` | `__main__.py` | 同 `mini` |

`mini` 的三个高级参数直接吃全路径：`--model-class` / `--agent-class` / `--environment-class`（`run/mini.py:57-59`）。

常用环境变量：`MSWEA_MODEL_NAME`、`MSWEA_MODEL_API_KEY`、`MSWEA_GLOBAL_COST_LIMIT`、`MSWEA_GLOBAL_CALL_LIMIT`、`MSWEA_COST_TRACKING=ignore_errors`、`MSWEA_MODEL_RETRY_STOP_AFTER_ATTEMPT`、`MSWEA_SILENT_STARTUP`、`MSWEA_CONFIG_DIR`、`MSWEA_DEFAULT_RUN`。

> 嵌入成库时注意：`minisweagent/__init__.py:26` 启动就 `mkdir` 全局配置目录并 `load_dotenv` 读 `~/.config/mini-swe-agent/.env`。做独立应用要换掉这层全局配置，否则会莫名读到用户机器上的全局 key。

## 三、循环本体：190 行，只有四个方法

`src/minisweagent/agents/default.py`

```python
def run(self, task="", **kw):        # 渲染 system / instance 模板 → while True: step()
                                     # 直到最后一条消息 role == "exit"；每步 finally 都 save()
def step(self):                      # = execute_actions(query())
def query(self):                     # ★ 文档字符串原文："Override to add hooks."
def execute_actions(self, message):  # 把 message["extra"]["actions"] 逐条交 env.execute，
                                     # 再把观察结果格式化回填消息
def save(self, path, *extra_dicts):  # trajectory 落盘（json）
```

### 3.1 可覆写的四个钩子

| 方法 | 默认实现（行号） | 我们拿它做什么 |
|---|---|---|
| `query()` | `130`：查 step/cost/时间限额 → `model.query()` → 累加 cost → `add_messages()` | **调模型前注入召回**（已在用） |
| `step()` | `126`：`execute_actions(query())` | 整步收尾（已在用） |
| `execute_actions(msg)` | `154`：逐条 `env.execute` → `format_observation_messages` → `add_messages` | 命令前置校验/拦截、非 bash 工具 |
| `add_messages(*msgs)` | `69`：`self.messages.extend(...)` | **所有消息的唯一漏斗**：审计、落库、打标包这里最省事 |

另有 `handle_uncaught_exception(e)`（`74`）、`serialize(*extra)`（`159`）可覆写。

**控制流是异常驱动的**：`exceptions.py` 里 `Submitted` / `LimitsExceeded` / `TimeExceeded` / `UserInterruption` / `FormatError` 全继承 `InterruptAgentFlow`，异常自己携带 messages，`run()` catch 完 append 进历史即可——**扩展不用改循环**。

### 3.2 终止信号：两个约定

1. **环境判完成**：`environments/local.py:48` 硬编码——输出**首行**等于 `COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT` 且返回码 0 → `raise Submitted(...)`。
2. **循环判退出**：`run()` 只看 `self.messages[-1]["role"] == "exit"`（`default.py:122`）。

→ 自定义"任务完成"信号只有两条路：**自己写 env 抛 `Submitted`**（推荐，不碰上游），或改上游（破坏"未改一行"口径）。
→ 我们的 `reply` 结束本轮走第 2 条：在 `step()` 里追加一条 `role="exit"`。

## 四、我们的改造：两个类，预计 < 120 行

| 类 | 覆写 | 挂什么 |
|---|---|---|
| `MemoryAgent(DefaultAgent)` | `query()` | 调模型**之前**把 `retrieve(query)` 的结果拼进上下文 |
| 同上 | `execute_actions()` | 动作执行**之后**把结果交给 `ingest()` 写记忆 |
| `ToolEnv`（实现 `Environment.execute`） | — | 把 bash-only 的动作空间换成**工具表**，其中含 `memory_search` / `memory_write` |

**写进方案的那句话**：宿主核心 190 行未改，仅新增 N 行适配（子类 + 环境），记忆层为自研 —— 比任何形容词都硬。

## 五、已知代价（别藏）

- 它的动作空间是**执行命令**（bash-only），面向 SWE-bench 之类的命令行任务 → 换工具调用是必做改造。
- 版本 2.4.6，官方有 v2 迁移指南（API 在演进，锁版本号）。
- 整包 `src/` = **5,349 行 / 59 个 `.py` 文件**（含多模型适配与基准脚本），我们只用得上 agents / models / environments / run 四块，真正进我们程序的只有 `default.py`(190) + `exceptions.py`(26) + `utils/` 几个小文件。

## 六、改不动的硬边界（提前知道，别踩）

| 边界 | 位置 | 绕法 |
|---|---|---|
| 工具名硬编码为 `bash`，别的名字直接 `FormatError` | `models/utils/actions_toolcall.py:61` | 自己实现 Model 协议换掉整个动作空间（我们走这条）；**不要**改上游 |
| "任务完成"信号硬编码在 env 里 | `environments/local.py:48` | 自己写 env 抛 `Submitted` |
| 无上下文压缩：`self.messages` 只增不减，trajectory == messages | `default.py:91-124` | 在 `query()` 里自己做历史处理（**我们最该补的一块**） |
| 无并发：每个 agent 实例单线程同步 | 全库 | 外层多进程/Ray（上游用 swebench runner） |
| 环境无状态：每条命令都是全新 subshell，`cd`/`export` 不跨步保留 | `environments/local.py:72-92` | 要么让模型写 `cd x && ...`，要么自己在 env 里维护会话 |
| 成本跟踪依赖 litellm 注册表，未注册的模型会 `RuntimeError` | `models/litellm_model.py:108` | `cost_tracking: ignore_errors` 或 `MSWEA_COST_TRACKING=ignore_errors` |

## 七、验证手段：假模型 + 自校验命令

上游自带确定性假模型（`models/test_models.py`），**零 API 花费就能跑通整条循环**，适合写自动化测试 / 演示前自检：

| 类 | 用途 |
|---|---|
| `DeterministicModel`（`test_models.py:104`） | 文本模式：喂一串预设动作 |
| `DeterministicToolcallModel`（`160`） | toolcall 模式（我们用的这种） |
| `DeterministicResponseAPIToolcallModel`（`218`） | `/response` 端点形态 |

配套 `make_output(content, actions, cost)` / `make_toolcall_output(content, tool_calls, actions)` 造轮次；注册名是 `deterministic`，`-c model.model_class=deterministic` 即可挂上。

自校验命令（不装依赖也能核对行数与接口）：

```bash
grep -c '' vendor/mini-swe-agent/src/minisweagent/agents/default.py   # 190
grep -n 'def \(query\|step\|execute_actions\|add_messages\)' \
  vendor/mini-swe-agent/src/minisweagent/agents/default.py
grep -c '' $(find vendor/mini-swe-agent/src -name '*.py') | awk -F: '{s+=$2} END {print s}'  # 5349
```
