# memagent/demo.py
# 端到端演示：FakeLLM（离线脚本化）+ 真实 memcore 记忆，跑一遍「有记忆的 agent」loop。

import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 让 memagent 找到同目录下姊妹项目 memcore（二者同属 ai_memory，非外部项目）
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "memcore"))

from memagent import Agent, FakeLLM, LLMResponse, ToolCall
from memcore import Memory

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo.db")
if os.path.exists(DB):
    os.remove(DB)
memory = Memory(DB)

# 脚本化 LLM：按 loop 实际调用顺序，预设每次 complete 的回复
script = [
    # 第 1 轮：用户说「我叫小明，喜欢咖啡」→ 模型主动 remember
    LLMResponse(tool_calls=[ToolCall(id="c1", name="remember",
                                     args={"content": "用户叫小明，喜欢咖啡",
                                           "keywords": ["用户", "喜好", "咖啡"]})]),
    LLMResponse(text="好的，我记住了。"),
    # 第 2 轮：用户问「我喜欢什么」→ 模型主动 recall
    LLMResponse(tool_calls=[ToolCall(id="c2", name="recall",
                                     args={"query": "喜欢 咖啡", "top_k": 3})]),
    LLMResponse(text="你喜欢咖啡。"),
]

llm = FakeLLM(script)
agent = Agent(llm, memory=memory, auto_inject=False, verbose=True)

print("=" * 64)
print("场景：一个有长期记忆的 agent（loop + 记忆工具）")
print("=" * 64)

print("\n用户：我叫小明，喜欢咖啡")
print(f"Agent：{agent.run('我叫小明，喜欢咖啡')}")

print("\n用户：我喜欢什么？")
print(f"Agent：{agent.run('我喜欢什么？')}")

print("\n--- 记忆库内容（memcore 落盘结果）---")
for m in memory.all():
    print(f"  {m['id'][:8]}  kw={m['keywords']}  w={m['weight']:.2f}  {m['content']}")

print("\n--- 完整对话历史（loop 里 LLM 实际看到的消息）---")
for i, msg in enumerate(agent.history):
    role = msg["role"]
    if msg.get("tool_calls"):
        detail = [tc["function"]["name"] for tc in msg["tool_calls"]]
    else:
        detail = msg.get("content")
    print(f"  [{i}] {role}: {detail}")

memory.close()
print("\n完成。数据库文件:", DB)
