# memagent/run_real.py
# 真实 DeepSeek 联调：读 .env 里的 DEEPSEEK_API_KEY，跑真实「有记忆的 agent」。
# 用两个独立会话共享同一记忆库，验证「跨对话记忆」：会话 2 无历史，只能靠 recall。

import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "memcore"))


def _load_env(path):
    """极简 .env 加载（保持零第三方依赖）。"""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


_load_env(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

from memagent import Agent, DeepSeekLLM
from memcore import Memory

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "real.db")
if os.path.exists(DB):
    os.remove(DB)
memory = Memory(DB)
llm = DeepSeekLLM()

print("=" * 64)
print("真实 DeepSeek 联调：跨对话记忆")
print("=" * 64)

print("\n会话 1（新对话，让模型记住个人信息）")
agent1 = Agent(llm, memory=memory, auto_inject=False, verbose=True)
print(f"用户：我叫小明，喜欢喝咖啡\nAgent：{agent1.run('我叫小明，喜欢喝咖啡')}")

print("\n会话 2（全新对话，历史清空，只剩长期记忆）")
agent2 = Agent(llm, memory=memory, auto_inject=False, verbose=True)
print(f"用户：我叫什么名字？喜欢喝什么？\nAgent：{agent2.run('我叫什么名字？喜欢喝什么？')}")

print("\n--- 记忆库（memcore 落盘）---")
for m in memory.all():
    print(f"  {m['id'][:8]}  kw={m['keywords']}  w={m['weight']:.2f}  {m['content']}")

memory.close()
print("\n完成。数据库文件:", DB)
