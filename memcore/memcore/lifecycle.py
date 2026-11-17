# memcore/lifecycle.py
# 生命周期：decay（遗忘）/ reinforce（巩固）/ consolidate（合并）/ replay（重放）/ tier（分层）。
# 只依赖 store 的公开 API，不碰 sqlite 细节。

from datetime import datetime, timezone

# 分层阈值与权重上下限
HOT = 0.7
COLD = 0.3
MAX_WEIGHT = 2.0
BOOST = 0.1


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def tier_of(weight: float) -> str:
    if weight >= HOT:
        return "hot"
    if weight >= COLD:
        return "warm"
    return "cold"


def decay(store, factor=0.9):
    """遗忘：全体权重 × factor，并重新分层。返回降层到 cold 的 id 列表。"""
    dropped = []
    for mem in store.all():
        w = mem["weight"] * factor
        t = tier_of(w)
        store.update_fields(mem["id"], weight=w, tier=t)
        if t == "cold":
            dropped.append(mem["id"])
    return dropped


def reinforce(store, mid, boost=BOOST):
    """巩固：命中一次，权重 +boost，cold 自动升回（刺激找回）。返回新权重。"""
    mem = store.get(mid)
    if not mem:
        return None
    w = min(mem["weight"] + boost, MAX_WEIGHT)
    store.update_fields(
        mid,
        weight=w,
        tier=tier_of(w),
        access_count=mem["access_count"] + 1,
        last_access=_now(),
    )
    return w


def retier(store):
    """按当前权重重算所有记忆的分层。"""
    for mem in store.all():
        store.update_fields(mem["id"], tier=tier_of(mem["weight"]))


def _jaccard(a, b):
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


def consolidate(store, index, overlap=0.5):
    """巩固：合并关键词高度重叠的近重复记忆，释放冗余。返回被合并（删除）的 id 列表。

    已知简化：O(n²) 两两比较，适合小规模记忆；大容量应换增量去重。
    """
    memories = store.all()
    merged = []
    removed = set()
    for i in range(len(memories)):
        if memories[i]["id"] in removed:
            continue
        for j in range(i + 1, len(memories)):
            if memories[j]["id"] in removed:
                continue
            a, b = memories[i], memories[j]
            if _jaccard(set(a["keywords"]), set(b["keywords"])) < overlap:
                continue
            # 合并：关键词取并集，保留权重更高者的原文，权重取平均
            keeper, dropped = (a, b) if a["weight"] >= b["weight"] else (b, a)
            new_kw = list(set(a["keywords"]) | set(b["keywords"]))
            avg_w = (a["weight"] + b["weight"]) / 2
            store.update_fields(keeper["id"], keywords=new_kw, weight=avg_w)
            store.delete(dropped["id"])
            merged.append(dropped["id"])
            removed.add(dropped["id"])
    # 合并后重建索引，避免关键词映射漂移
    index.build(store.all())
    return merged


def replay(store, n=3):
    """重放：挑权重最低的 n 条（不含已 cold）重放一次，模拟巩固到长期记忆。返回重放的 id。"""
    alive = [m for m in store.all() if m["tier"] != "cold"]
    alive.sort(key=lambda m: m["weight"])
    picked = alive[:n]
    for m in picked:
        reinforce(store, m["id"])
    return [m["id"] for m in picked]
