# memcore/demo.py
# 端到端演示：完整生命周期（存 → 检索 → 遗忘 → 巩固 → 合并 → 重放 → 分层）。

import os
import sys

# Windows 控制台默认 GBK，强制 UTF-8 输出，避免中文乱码
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from memcore import Memory

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo.db")
if os.path.exists(DB):
    os.remove(DB)

mem = Memory(DB)

print("=" * 64)
print("1) 存入记忆（原文无损 + 关键词索引）")
mem.add("对手第一轮就背叛了我", keywords=["对手", "背叛"])
mem.add("对方连续三次背叛，我开始报复", keywords=["对手", "背叛", "报复"])
mem.add("合作能带来双方收益，我倾向合作", keywords=["合作", "收益"])
mem.add("当对方反复背叛时，报复是理性选择", keywords=["背叛", "报复", "理性"])
for m in mem.all():
    print(f"   {m['id'][:8]}  kw={m['keywords']}  w={m['weight']:.2f}  tier={m['tier']}")

print("\n2) 检索「对方背叛我该怎么办」")
for m in mem.retrieve("对方背叛我该怎么办", top_k=3):
    print(f"   [{m['tier']}] w={m['weight']:.2f}  {m['content']}")

print("\n3) 连续遗忘 6 次（每次 ×0.9）")
for _ in range(6):
    mem.decay()
print("   stats:", mem.stats())

print("\n4) 再次检索（cold 已被排除）")
hits = mem.retrieve("对方背叛我该怎么办", top_k=3)
print(f"   命中 {len(hits)} 条：", [m['content'][:12] for m in hits])

print("\n5) 合并近重复（关键词重叠 ≥ 0.5）")
merged = mem.consolidate(overlap=0.5)
print(f"   合并 {len(merged)} 条 -> stats: {mem.stats()}")

print("\n6) 重放最低权重记忆（巩固到长期）")
replayed = mem.replay(n=2)
print(f"   重放 {len(replayed)} 条")

print("\n7) 最终 stats:")
print("  ", mem.stats())

mem.close()
print("\n完成。数据库文件:", DB)
