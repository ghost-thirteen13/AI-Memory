# memcore/memory.py
# 门面：把存储 / 索引 / 关键词 / 生命周期串成对外干净 API。

from datetime import datetime, timezone

from .store import Store
from .index import Index
from .keywords import extract_keywords
from . import lifecycle

# 检索 recency 打分半衰期（小时）
HALF_LIFE_HOURS = 24.0


class Memory:
    """独立 AI 记忆小系统。

    用法：
        mem = Memory("mem.db")
        mem.add("对手连续背叛我三次", keywords=["对手", "背叛"])
        hits = mem.retrieve("对手总背叛我")
        mem.decay(); mem.consolidate(); mem.replay()
        mem.close()
    """

    def __init__(self, db_path: str, extractor=None):
        self.store = Store(db_path)
        self.index = Index()
        self.index.build(self.store.all())
        self.extractor = extractor or extract_keywords

    # ---- 写 ----
    def add(self, content: str, keywords=None, weight=1.0):
        """存入一条记忆。未给关键词则用提取器自动生成。返回 id（按原文哈希去重）。"""
        if keywords is None:
            keywords = self.extractor(content)
        mid, _created = self.store.upsert(content, keywords, weight=weight)
        # 让索引与该 id 的关键词保持一致：先清旧映射，再加新的
        self.index.remove(mid, self.index.keywords_of(mid))
        for kw in keywords:
            self.index.add(kw, mid)
        return mid

    # ---- 读 ----
    def all(self):
        return self.store.all()

    def retrieve(self, query: str, top_k=5, include_cold=False):
        """检索：关键词交集 → 空则并集 → 再空则退化到全部热记忆；命中即巩固（权重回升）。"""
        q_kw = self.extractor(query)
        ids = self.index.lookup(q_kw)
        if not ids:
            ids = self.index.lookup_union(q_kw)
        if not ids:
            ids = {m["id"] for m in self.store.all() if m["tier"] != "cold"}

        rows = [self.store.get(mid) for mid in ids]
        rows = [r for r in rows if r and (include_cold or r["tier"] != "cold")]
        rows.sort(key=self._score, reverse=True)
        picked = rows[:top_k]
        for r in picked:
            lifecycle.reinforce(self.store, r["id"])
        return picked

    def _score(self, mem):
        """recency 打分：weight × 2^(-age_hours / 24)（Ebbinghaus 半衰期）。"""
        try:
            t = datetime.fromisoformat(mem["updated_at"])
        except Exception:
            return mem["weight"]
        age_hours = (datetime.now(timezone.utc) - t).total_seconds() / 3600.0
        return mem["weight"] * (2 ** (-age_hours / HALF_LIFE_HOURS))

    # ---- 生命周期 ----
    def decay(self, factor=0.9):
        return lifecycle.decay(self.store, factor)

    def consolidate(self, overlap=0.5):
        return lifecycle.consolidate(self.store, self.index, overlap)

    def replay(self, n=3):
        return lifecycle.replay(self.store, n)

    def forget(self, mid):
        """软遗忘：降为 cold（不删数据，可被找回）。"""
        self.store.update_fields(mid, tier="cold")

    def remember(self, mid):
        """找回：cold 升回 hot，权重复位 1.0。"""
        self.store.update_fields(mid, tier="hot", weight=1.0)

    def stats(self):
        mems = self.store.all()
        tiers = {"hot": 0, "warm": 0, "cold": 0}
        for m in mems:
            tiers[m["tier"]] = tiers.get(m["tier"], 0) + 1
        return {"total": len(mems), "tiers": tiers, "index": self.index.stats()}

    def close(self):
        self.store.close()
