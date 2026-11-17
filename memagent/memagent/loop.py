# memagent/loop.py
# 核心 harness loop：LLM ↔ 工具执行 的闭环。这是整个系统的「心脏」。

import json


def run_loop(llm, registry, messages, max_steps=10, tool_schemas=None, verbose=False):
    """跑一个 loop，直到 LLM 不再调用工具（给出最终回答）或到达 max_steps。

    返回 (最终文本, 完整消息历史, 实际步数)。
    """
    for step in range(max_steps):
        resp = llm.complete(messages, tools=tool_schemas)

        # 没有工具调用 → LLM 已给出最终回答，循环结束。
        # 对应 nanocode 的「if not tool_results: break」——工具链耗尽即收尾。
        if not resp.tool_calls:
            if verbose:
                print(f"[step {step}] LLM 直接回答：{resp.text!r}")
            # 把最终回答也写进历史，下一轮模型才能看到自己上一句答复
            if resp.text:
                messages.append({"role": "assistant", "content": resp.text})
            return resp.text or "", messages, step

        # 有工具调用 → 先把 assistant 的 tool_calls 记进历史
        messages.append({
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.name,
                                 "arguments": json.dumps(tc.args, ensure_ascii=False)},
                }
                for tc in resp.tool_calls
            ],
        })

        # 逐个执行工具，把结果作为「tool」消息塞回。
        # tool_call_id 必须对齐，LLM 才知道每条结果对应哪个调用。
        for tc in resp.tool_calls:
            result = registry.execute(tc.name, tc.args)
            if verbose:
                print(f"[step {step}] 调用工具 {tc.name}{tc.args} -> {result!r}")
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": str(result),
            })

    # 到达 max_steps 仍未收敛
    if verbose:
        print(f"[step {max_steps}] 达到最大步数，强制结束")
    return "(达到最大步数，强制结束)", messages, max_steps
