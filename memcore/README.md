# memcore —— 独立 AI 记忆小系统

一个零依赖（纯标准库）的 AI Agent 记忆系统，把「AI 记忆研究」里批判性提取出的可信干货，落成可运行的最小实现。**独立存在，不关联任何现有项目。**

## 一句话原理

**索引 + 哈希 ID + 原文无损 + 软遗忘**：记忆不把正文直接堆给模型，而是存「关键词索引 → 哈希 ID → 原文」；遗忘是降权找回，不是物理删除。

## 每部分是什么 / 有什么

| 文件 | 是什么 | 有什么 |
|---|---|---|
| `memcore/store.py` | 存储层 | SQLite 单表；哈希主键去重；原文无损；`tier` 分层字段；`upsert/get/all/update_fields/delete` |
| `memcore/index.py` | 索引层 | 关键词→ID 倒排索引；`lookup`（交集）/`lookup_union`（并集）；`alias`（合并）/`expand`（展开，嵌套集合） |
| `memcore/keywords.py` | 关键词层 | 机械默认提取器（零依赖）；可注入自定义提取器——换成 LLM 即「让 AI 自己管理记忆」 |
| `memcore/lifecycle.py` | 生命周期 | `decay`（遗忘）/`reinforce`（巩固）/`consolidate`（合并）/`replay`（重放）/`tier_of`（分层） |
| `memcore/memory.py` | 门面 | 对外唯一 API `Memory`：`add/retrieve/decay/consolidate/replay/forget/remember/stats` |
| `demo.py` | 演示 | 端到端跑一遍完整生命周期 |
| `test_memcore.py` | 单测 | 5 个用例断言核心行为 |

## 数据模型（单表 `memories`）

| 字段 | 类型 | 含义 |
|---|---|---|
| `id` | TEXT PK | sha256(原文)，外部约束去重 |
| `content` | TEXT | 原文，无损 |
| `keywords` | TEXT | JSON 数组，索引层来源 |
| `weight` | REAL | 权重，默认 1.0，软遗忘衰减 |
| `created_at` / `updated_at` | TEXT | 时间戳 |
| `access_count` | INT | 命中次数 |
| `last_access` | TEXT | 最近命中时间 |
| `tier` | TEXT | hot / warm / cold 分层 |

**检索打分**：`score = weight × 2^(-age_hours / 24)`（Ebbinghaus 半衰期 24h）。命中即 `reinforce`（权重 +0.1，封顶 2.0，cold 自动升回）。
**分层阈值**：weight ≥ 0.7 = hot；≥ 0.3 = warm；< 0.3 = cold（默认检索排除，数据仍在，可 `remember` 找回）。

## 研究干货 → 组件映射（已落地）

| 研究干货 | 落点 | 状态 |
|---|---|---|
| 存索引 + 哈希 ID，原内容无损 | `store.py` + `index.py` | ✅ 已落地 |
| 让 AI 自己管理记忆 | `keywords.py` 可插拔提取器 | ✅ 留钩子（默认机械版） |
| 遗忘 = 降权找回（软遗忘） | `lifecycle.py` 的 `decay`/`forget`/`reinforce` | ✅ 已落地 |
| 缓存 / 长期记忆分层 | `tier` 字段 | ✅ 已落地 |
| 索引可合并 / 展开、嵌套集合 | `index.py` 的 `alias`/`expand` | ✅ 已落地 |
| 巩固-重放-遗忘完整生命周期 | `lifecycle.py` 的 `consolidate`/`replay`/`decay` | ✅ 已落地 |
| 红线：快编码 vs 慢提取分开 | 检索（倒排）与统计（权重/分层）互不污染 | ✅ 结构上分开 |

**已排除**（研究里「该打折」的）：CFD/状态转移方程、向量检索（太重，用倒排替代）、图数据库（最小实现不需要）。

## 快速开始

```bash
cd D:\Desktop\ai_memory\memcore
py -3.11 -m unittest test_memcore -v   # 跑单测
py -3.11 demo.py                        # 跑端到端演示
```

```python
from memcore import Memory

mem = Memory("memory.db")
mem.add("对手连续三次背叛，我开始报复", keywords=["对手", "背叛", "报复"])
hits = mem.retrieve("对方背叛我该怎么办", top_k=3)
mem.decay()          # 遗忘：全体权重衰减
mem.consolidate()    # 巩固：合并近重复记忆
mem.replay()         # 重放：找回最低权重记忆
print(mem.stats())
mem.close()
```

## 生命周期怎么串起来

1. **存**：`add(content)` → 哈希算 ID → 抽关键词 → 入表 + 建索引。
2. **取**：`retrieve(query)` → 抽关键词 → 索引交集（空则并集）→ 按 `weight × recency` 排序 → 命中即巩固。
3. **忘**：`decay()` 全体降权、`forget(id)` 单条降为 cold（数据仍在）。
4. **整**：`consolidate()` 合并关键词高度重叠的近重复；`replay()` 把最低权重记忆重放巩固。
5. **分层**：权重自动映射 hot/warm/cold，冷记忆不参与默认检索但可找回。

## 边界与已知简化

- 不接真实 LLM（只留 `extractor` 钩子），保持零依赖、可离线跑。
- 不上向量 / 图数据库；检索是关键词倒排（索引交集）。
- `consolidate` 为 O(n²) 两两比较，适合小规模记忆，大容量需换增量去重。
- 无并发保护，单进程使用。

## 呼应规划

设计推演与每步 CoT 见 `..\work\map\`：
- `00_规范流程.md` —— 操作纪律（先规划-再执行）
- `01_CoT_规划.md` —— 本系统的完整设计推演
- `02_执行日志.md` —— 每步的目标/推理/决策/结果
