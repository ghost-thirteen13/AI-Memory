# memagent/llm.py
# LLM 抽象：统一「纯文本回复」与「工具调用回复」两种结果。
# 内置 FakeLLM（离线脚本化，可测可演示）、DeepSeekLLM（真实适配，纯 stdlib urllib）。

import json
import os
from dataclasses import dataclass, field
from urllib import request


@dataclass
class ToolCall:
    id: str
    name: str
    args: dict


@dataclass
class LLMResponse:
    text: str | None = None                      # 无工具调用时的最终回答
    tool_calls: list = field(default_factory=list)  # 有工具调用时非空


class LLM:
    """LLM 抽象接口。子类只需实现 complete(messages, tools=None) -> LLMResponse。"""

    def complete(self, messages, tools=None):
        raise NotImplementedError


class FakeLLM(LLM):
    """脚本化假 LLM：按顺序吐出预设回复。离线可跑、可测，用于演示 loop。"""

    def __init__(self, script):
        self._script = list(script)   # list[LLMResponse]，按调用顺序弹出
        self.calls = []               # 记录每次入参，便于断言/观察

    def complete(self, messages, tools=None):
        self.calls.append(messages)
        if not self._script:
            return LLMResponse(text="(FakeLLM 脚本已耗尽)")
        return self._script.pop(0)


class DeepSeekLLM(LLM):
    """真实 DeepSeek（OpenAI 兼容）适配器，纯 stdlib urllib，无第三方依赖。

    需要 api_key 或环境变量 DEEPSEEK_API_KEY。
    ⚠️ 实机未在离线测试覆盖；按 OpenAI 兼容格式实现，用前自行核对 DeepSeek 当前协议。
    """

    def __init__(self, api_key=None, model="deepseek-chat",
                 base_url="https://api.deepseek.com/chat/completions", debug=False):
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("DeepSeekLLM 需要 api_key 或环境变量 DEEPSEEK_API_KEY")
        self.model = model
        self.base_url = base_url
        self.debug = debug

    def complete(self, messages, tools=None):
        body = {"model": self.model, "messages": messages, "temperature": 0.7}
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"
        if self.debug:
            tool_names = [t["function"]["name"] for t in (tools or [])]
            print(f"[DeepSeekLLM] 发送请求：tools={tool_names} 末条消息={messages[-1]['role']}")
        req = request.Request(
            self.base_url,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )
        with request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        msg = data["choices"][0]["message"]
        tool_calls = []
        for tc in (msg.get("tool_calls") or []):
            tool_calls.append(ToolCall(
                id=tc["id"],
                name=tc["function"]["name"],
                args=json.loads(tc["function"].get("arguments") or "{}"),
            ))
        return LLMResponse(text=msg.get("content"), tool_calls=tool_calls)
