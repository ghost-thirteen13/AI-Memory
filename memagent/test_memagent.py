# memagent/test_memagent.py
# 单测：用 FakeLLM 离线验证 loop 与工具执行、记忆工具端到端。

import unittest

from memagent import Agent, FakeLLM, LLMResponse, ToolCall
from memagent.tools import ToolRegistry, register_memory_tools


class FakeMemory:
    """鸭式记忆：只实现 add/retrieve，用于证明 harness 与记忆解耦。"""

    def __init__(self):
        self.rows = []

    def add(self, content, keywords=None, weight=1.0):
        self.rows.append({"content": content, "keywords": keywords or []})
        return f"fakeid{len(self.rows)}"

    def retrieve(self, query, top_k=5, include_cold=False):
        return [r for r in self.rows
                if any(k in query for k in r["keywords"])][:top_k]


def _echo_registry():
    reg = ToolRegistry()
    reg.register("echo", lambda x: x, "echo", {
        "type": "object",
        "properties": {"x": {"type": "string"}},
        "required": ["x"],
    })
    return reg


class LoopTest(unittest.TestCase):
    def test_single_tool_then_text(self):
        llm = FakeLLM([
            LLMResponse(tool_calls=[ToolCall("c1", "echo", {"x": "hi"})]),
            LLMResponse(text="done"),
        ])
        agent = Agent(llm)
        agent.tools = _echo_registry()
        out = agent.run("hi")
        self.assertEqual(out, "done")
        self.assertIn("tool", [m["role"] for m in agent.history])

    def test_parallel_tool_calls(self):
        llm = FakeLLM([
            LLMResponse(tool_calls=[
                ToolCall("c1", "echo", {"x": "a"}),
                ToolCall("c2", "echo", {"x": "b"}),
            ]),
            LLMResponse(text="done"),
        ])
        agent = Agent(llm)
        agent.tools = _echo_registry()
        out = agent.run("x")
        self.assertEqual(out, "done")
        tool_msgs = [m for m in agent.history if m["role"] == "tool"]
        self.assertEqual(len(tool_msgs), 2)

    def test_max_steps_forced_stop(self):
        llm = FakeLLM([LLMResponse(tool_calls=[ToolCall("c1", "echo", {"x": "loop"})])] * 20)
        agent = Agent(llm, max_steps=3)
        agent.tools = _echo_registry()
        out = agent.run("x")
        self.assertIn("最大步数", out)

    def test_unknown_tool_returns_error(self):
        llm = FakeLLM([
            LLMResponse(tool_calls=[ToolCall("c1", "nope", {})]),
            LLMResponse(text="done"),
        ])
        agent = Agent(llm)
        out = agent.run("x")
        self.assertEqual(out, "done")
        tool_msg = [m for m in agent.history if m["role"] == "tool"][0]
        self.assertIn("未知工具", tool_msg["content"])


class MemoryToolsTest(unittest.TestCase):
    def test_remember_then_recall(self):
        mem = FakeMemory()
        reg = ToolRegistry()
        register_memory_tools(reg, mem)
        reg.execute("remember", {"content": "用户喜欢咖啡", "keywords": ["咖啡"]})
        self.assertEqual(len(mem.rows), 1)
        result = reg.execute("recall", {"query": "咖啡", "top_k": 3})
        self.assertIn("咖啡", result)

    def test_memory_agent_end_to_end(self):
        mem = FakeMemory()
        llm = FakeLLM([
            LLMResponse(tool_calls=[ToolCall("c1", "remember",
                                             {"content": "用户喜欢咖啡",
                                              "keywords": ["咖啡"]})]),
            LLMResponse(text="记住了"),
            LLMResponse(tool_calls=[ToolCall("c2", "recall", {"query": "咖啡"})]),
            LLMResponse(text="你喜欢咖啡"),
        ])
        agent = Agent(llm, memory=mem, auto_inject=False)
        self.assertEqual(agent.run("我叫小明，喜欢咖啡"), "记住了")
        self.assertEqual(agent.run("我喜欢什么"), "你喜欢咖啡")
        self.assertEqual(len(mem.rows), 1)


if __name__ == "__main__":
    unittest.main()
