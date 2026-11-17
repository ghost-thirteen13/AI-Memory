# memcore/keywords.py
# 关键词提取：默认机械版（零依赖、可离线），可注入自定义提取器（如 LLM）。

import re

# 中文常见虚词，防止索引被噪声词淹没
_STOPWORDS = {
    "的", "了", "是", "在", "我", "你", "他", "她", "它", "们", "这", "那",
    "和", "与", "或", "及", "对", "就", "都", "而", "被", "把", "一个",
    "我们", "你们", "他们", "自己", "已经", "因为", "所以", "如果", "但是",
    "不是", "没有", "可以", "还是", "就是", "这个", "那个", "什么", "怎么",
}


def extract_keywords(content: str, max_k: int = 6) -> list:
    """机械默认提取器：切词 → 去停用词 → 去重 → 长词优先。

    说明：这是「离线可跑」的占位实现；真实场景应注入 LLM 提取器，
    让模型自己写关键词（对应研究里「让 AI 自己管理记忆」）。
    """
    if not content:
        return []
    # 切出「英文/数字词」或「连续中文片段」
    tokens = re.findall(r"[A-Za-z0-9_]+|[一-鿿]+", content)
    candidates = []
    for t in tokens:
        if re.match(r"^[A-Za-z0-9_]+$", t):
            if len(t) >= 2:
                candidates.append(t.lower())
        else:
            if len(t) >= 2:
                candidates.append(t)          # 整个中文片段（更具体）
            for i in range(len(t) - 1):        # 相邻二元组（提升召回）
                candidates.append(t[i:i + 2])
    seen, result = set(), []
    for w in candidates:
        if w in _STOPWORDS or w in seen:
            continue
        seen.add(w)
        result.append(w)
    # 长词更具体，优先保留
    result.sort(key=len, reverse=True)
    return result[:max_k]
