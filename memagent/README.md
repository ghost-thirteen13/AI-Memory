# memagent —— 有记忆的 agent（nanocode 的 loop + memcore 的 Memory）

零第三方依赖、可离线演示的「有记忆的 agent」。把 nanocode 学到的 harness loop 与 memcore 的记忆系统结合，独立存在，不关联任何现有项目。

## 一句话原理

**loop + state**：nanocode 的「LLM↔工具闭环」= 循环；memcore = 跨对话状态。结合 = 一个有长期记忆、且自己管理记忆的 agent。

## 每部分是什么 / 有什么

| 文件 | 是什么 | 有什么 |
|---|---|---|
| `memagent/llm.py` | LLM 抽象 | `LLM` 接口 + `FakeLLM`（离线脚本化）+ `DeepSeekLLM`（真实适配，stdlib urllib） |
| `memagent/tools.py` | 工具注册表 | `ToolRegistry`（注册/执行/产出 OpenAI schema）+ 记忆工具 `remember`/`recall` |
| `memagent/loop.py` | 核心 loop | `run_loop`：LLM↔工具闭环，无工具调用即收尾 |
| `memagent/agent.py` | 门面 Agent | 把 LLM+工具+记忆串起来；上下文历史=缓存，memcore=长期记忆 |
| `demo.py` | 演示 | FakeLLM + 真 memcore 跑 `remember → recall` 两轮 |
| `test_memagent.py` | 单测 | 6 用例断言 loop 与记忆工具行为 |

## 核心机制：让 AI 自己管理记忆

「让 AI 自己管理记忆，人只拿哈希做外部约束」的落点，就是 loop 里的 tool 机制：

- 把 `Memory.add/retrieve` 包成 `remember`/`recall` 两个工具。
- 模型自己决定何时存、何时查；harness 只负责执行、把结果塞回对话。
- 人（memcore 的哈希主键）做外部约束：同一原文只存一份。

## loop 长什么样（心脏）

```
messages = [system] + 长期记忆兜底注入(可选) + 短期历史 + [user 本轮]
for step in range(max_steps):
    resp = llm.complete(messages)
    if 没有 tool_calls:            # 工具链耗尽 → 收尾（对应 nanocode 的 break）
        写回最终回答，return
    执行每个 tool_call，结果作为 tool 消息塞回（tool_call_id 对齐）
```

## 分层

- **短期记忆** = 本会话的 messages 历史（含工具往返），下一轮自动带入 —— 对应「缓存（前额叶+海马体）」。
- **长期记忆** = memcore（跨对话沉淀、会遗忘会巩固）—— 对应「皮层」。
- **注入两模式**：A 工具主动 `recall`（主）+ B `auto_inject` 兜底注入 top1（可关）。

## 运行

```bash
cd D:\Desktop\ai_memory\memagent
py -3.11 -m unittest test_memagent -v   # 跑单测
py -3.11 demo.py                         # 跑端到端演示
```

## 接真实 LLM

已用真实 DeepSeek 跑通「跨对话记忆」：`run_real.py` 用两个独立会话共享同一记忆库，会话 1 让模型 `remember`，会话 2 历史清空、模型只能靠 `recall` 答对。

```bash
cd D:\Desktop\ai_memory\memagent
py -3.11 run_real.py    # 读 .env 里的 DEEPSEEK_API_KEY，跑真实联调
```

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "memcore"))

from memagent import Agent, DeepSeekLLM
from memcore import Memory

llm = DeepSeekLLM()                       # 读环境变量 DEEPSEEK_API_KEY
agent = Agent(llm, memory=Memory("mem.db"))
print(agent.run("你好，我叫小明"))
```

**实机已踩过的坑**：系统提示必须**强制**模型调用工具（「禁止只口头说记住了」），否则模型会客套地回「我记住了」却不真正调用 `remember`。见 `agent.py` 的 `DEFAULT_SYSTEM`。

`DEEPSEEK_API_KEY` 存 `memagent\.env`（勿提交到任何仓库）。

## 呼应规划

见 `..\work\map\`：`03_结合_CoT规划.md`（设计推演）、`04_结合_执行日志.md`（每步 CoT）。
