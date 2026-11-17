# memagent/tools.py
# 工具注册表 + 记忆工具（remember/recall）。实现「让 AI 自己管理记忆」。


class ToolRegistry:
    """工具注册表：登记 name→(函数, 描述, 参数schema)，负责执行 + 产出 OpenAI schema。"""

    def __init__(self):
        self._tools = {}

    def register(self, name, fn, description, params):
        self._tools[name] = {"fn": fn, "description": description, "params": params}

    def execute(self, name, args):
        if name not in self._tools:
            return f"[错误] 未知工具：{name}"
        try:
            return self._tools[name]["fn"](**(args or {}))
        except TypeError as e:
            return f"[参数错误] {e}"
        except Exception as e:
            return f"[工具执行失败] {e}"

    def schemas(self):
        """OpenAI function-calling 格式的 tool schema（供真实 LLM 用）。"""
        return [{
            "type": "function",
            "function": {
                "name": name,
                "description": t["description"],
                "parameters": t["params"],
            },
        } for name, t in self._tools.items()]


def register_memory_tools(registry, memory):
    """把记忆对象（需有 add/retrieve）包成两个工具。"""
    def remember(content: str, keywords: list = None):
        mid = memory.add(content, keywords=keywords)
        return f"已记住（id={mid[:8]}）"

    def recall(query: str, top_k: int = 3):
        hits = memory.retrieve(query, top_k=top_k)
        if not hits:
            return "没有相关记忆。"
        return "\n".join(f"- {h['content']}" for h in hits)

    registry.register(
        "remember", remember,
        "把一条重要信息存入长期记忆，可附关键词。",
        {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "要记住的原文"},
                "keywords": {"type": "array", "items": {"type": "string"},
                             "description": "可选关键词列表"},
            },
            "required": ["content"],
        },
    )
    registry.register(
        "recall", recall,
        "按语义关键词检索长期记忆，返回最相关的记忆。",
        {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "检索关键词或问题"},
                "top_k": {"type": "integer", "description": "返回条数"},
            },
            "required": ["query"],
        },
    )
    return registry
