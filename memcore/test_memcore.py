# memcore/test_memcore.py
# 单测：验证核心行为（去重 / 检索 / 软遗忘 / 巩固 / 合并 / 找回）。

import os
import tempfile
import unittest

from memcore import Memory


class MemoryTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        self.path = tmp.name
        self.mem = Memory(self.path)

    def tearDown(self):
        self.mem.close()
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_add_dedup_by_hash(self):
        id1 = self.mem.add("对方背叛我")
        id2 = self.mem.add("对方背叛我")
        self.assertEqual(id1, id2)
        self.assertEqual(self.mem.stats()["total"], 1)

    def test_retrieve_matches_keywords(self):
        self.mem.add("对方背叛我", keywords=["背叛"])
        self.mem.add("合作收益高", keywords=["合作"])
        hits = self.mem.retrieve("背叛怎么办", top_k=5)
        self.assertTrue(any("背叛" in h["content"] for h in hits))

    def test_decay_lowers_weight_and_tier(self):
        mid = self.mem.add("一条会遗忘的记忆", keywords=["遗忘"])
        before = self.mem.store.get(mid)["weight"]
        for _ in range(20):
            self.mem.decay()
        after = self.mem.store.get(mid)
        self.assertLess(after["weight"], before)
        self.assertEqual(after["tier"], "cold")

    def test_forget_is_soft(self):
        mid = self.mem.add("软遗忘测试", keywords=["软遗忘"])
        self.mem.forget(mid)
        self.assertEqual(self.mem.store.get(mid)["tier"], "cold")  # 数据仍在
        self.mem.remember(mid)
        self.assertEqual(self.mem.store.get(mid)["tier"], "hot")

    def test_consolidate_merges_near_dupes(self):
        self.mem.add("对方反复背叛", keywords=["背叛", "对手"])
        self.mem.add("对手老背叛", keywords=["背叛", "对手"])
        total_before = self.mem.stats()["total"]
        merged = self.mem.consolidate(overlap=0.5)
        self.assertGreaterEqual(len(merged), 1)
        self.assertLess(self.mem.stats()["total"], total_before)


if __name__ == "__main__":
    unittest.main()
