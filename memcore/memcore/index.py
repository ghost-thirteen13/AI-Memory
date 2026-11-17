# memcore/index.py
# 索引层：关键词 → 记忆 ID 的倒排索引。
# 支持 alias（合并）/ expand（展开），实现「索引可合并/展开、嵌套集合」。

from collections import defaultdict


class Index:
    def __init__(self):
        self._kw2ids = defaultdict(set)  # keyword -> set(memory_id)
        self._aliases = {}               # alias -> frozenset(成员关键词)

    # ---- 构建 / 增删 ----
    def build(self, rows):
        """从 store 读出的行（含 keywords 字段）重建索引。"""
        self._kw2ids = defaultdict(set)
        for r in rows:
            for kw in r["keywords"]:
                self._kw2ids[kw].add(r["id"])

    def add(self, keyword, memory_id):
        self._kw2ids[keyword].add(memory_id)

    def remove(self, memory_id, keywords):
        for kw in keywords:
            self._kw2ids[kw].discard(memory_id)

    # ---- 查询 ----
    def lookup(self, keywords):
        """索引交集：多个关键词都命中的 memory_id 集合。"""
        if not keywords:
            return set()
        sets = [self._kw2ids[k] for k in keywords if k in self._kw2ids]
        if not sets:
            return set()
        return set.intersection(*sets)

    def lookup_union(self, keywords):
        """索引并集：任意关键词命中的 memory_id 集合（交集为空时的退化路径）。"""
        ids = set()
        for k in keywords:
            ids |= self._kw2ids.get(k, set())
        return ids

    # ---- 合并 / 展开（嵌套集合）----
    def alias(self, name, member_keywords):
        """合并：把多个关键词归入一个别名（别名与成员都保留）。"""
        self._aliases[name] = frozenset(member_keywords)

    def expand(self, keyword):
        """展开：返回该关键词自身 + 其别名内所有成员关键词命中的 memory_id 并集。"""
        ids = set(self._kw2ids.get(keyword, set()))
        for alias, members in self._aliases.items():
            if keyword == alias or keyword in members:
                for m in members:
                    ids |= self._kw2ids.get(m, set())
        return ids

    def keywords_of(self, memory_id):
        """返回某个记忆当前挂在哪些关键词下（供 add 时清旧映射用）。"""
        return {kw for kw, ids in self._kw2ids.items() if memory_id in ids}

    def stats(self):
        return {"keywords": len(self._kw2ids), "aliases": len(self._aliases)}
