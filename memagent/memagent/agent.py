# memagent/agent.py
# 门面 Agent：把 LLM + 工具 + 记忆串成「有记忆的 agent」。
# 分层：上下文历史 = 缓存（前额叶+海马体）；memcore = 长期记忆（皮层）。

from .tools import ToolRegistry, register_memory_tools
from .loop import run_loop

DEFAULT_SYSTEM = (
    "你是一个有长期记忆的助手。必须严格遵守：\n"
    "1. 当用户说出任何关于他们自己的信息（名字、喜好、经历、事实等），"
    "你必须立即调用 remember 工具存入长期记忆；禁止只口头说「我记住了」而不调用工具。\n"
    "2. 当用户询问之前说过、但你现在没有上下文的信息时，"
    "必须先调用 recall 工具检索长期记忆再回答；若 recall 返回「没有相关记忆」，如实说你不记得。\n"
    "3. 只有既不需要存、也不需要查时，才直接回答。"
)


class Agent:
    def __init__(self, llm, memory=None, system_prompt=DEFAULT_SYSTEM,
                 max_steps=10, auto_inject=True, verbose=False):
        self.llm = llm
        self.memory = memory
        self.tools = ToolRegistry()
        if memory is not None:
            register_memory_tools(self.tools, memory)
        self.system_prompt = system_prompt
        self.max_steps = max_steps
        self.auto_inject = auto_inject
        self.verbose = verbose
        self.history = []   # 短期记忆：本会话完整消息历史（含工具往返）

    def run(self, user_input):
        # system 只加一次（历史为空时初始化），避免每轮重复
        if not self.history:
            self.history = [{"role": "system", "content": self.system_prompt}]

        messages = list(self.history)

        # 长期记忆兜底注入（模式 B）：临时注入，不写入 history
        if self.auto_inject and self.memory is not None:
            hits = self.memory.retrieve(user_input, top_k=1)
            if hits:
                messages.append({
                    "role": "user",
                    "content": f"[背景记忆] {hits[0]['content']}",
                })

        messages.append({"role": "user", "content": user_input})

        text, messages, _steps = run_loop(
            self.llm, self.tools, messages,
            max_steps=self.max_steps,
            tool_schemas=self.tools.schemas() or None,
            verbose=self.verbose,
        )
        self.history = messages   # 保留整段历史作为下一轮的短期记忆
        return text
