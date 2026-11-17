# AI-Memory

零第三方依赖（纯 Python 标准库）的 AI 记忆系统，由两个独立子系统组成。

## 这是什么

把「AI 记忆研究」里批判性提取的可信干货，落成可运行、可测试、可离线的代码：

- **memcore** —— 记忆存储核心。索引 + 哈希 ID + 原文无损 + 软遗忘（遗忘 = 降权找回，不是物理删除）。
- **memagent** —— 有记忆的 agent。nanocode 式 harness loop + memcore，把记忆包成 `remember`/`recall` 工具，「让 AI 自己管理记忆」。

## 核心思想

一句话：**loop + state**。harness 让 agent 跑起来（loop），记忆让 agent 跨对话不遗忘（state）。

「让 AI 自己管理记忆」的载体，是 loop 里的 tool 机制：把 `Memory.add/retrieve` 包成两个工具，模型自己决定何时存、何时查，人只拿哈希做外部约束。

## 结构

```
AI-Memory/
  memcore/     # 记忆存储核心（store / index / keywords / lifecycle / memory 五层）
  memagent/    # 有记忆的 agent（llm / tools / loop / agent 四层 + demo / 测试 / 真实联调）
```

各子系统的详细说明见各自的 `README.md`。

## 快速开始

```bash
# memcore：记忆系统（离线）
cd memcore
py -3.11 -m unittest test_memcore -v
py -3.11 demo.py

# memagent：有记忆的 agent（离线 FakeLLM）
cd ../memagent
py -3.11 -m unittest test_memagent -v
py -3.11 demo.py
```

## 接真实 LLM（DeepSeek）

memagent 内置 DeepSeek 适配器（纯 stdlib urllib），需要环境变量 `DEEPSEEK_API_KEY`：

```bash
# Windows
setx DEEPSEEK_API_KEY <你的key>

cd memagent
py -3.11 run_real.py    # 真实跨对话记忆联调
```

或复制 `.env.example` 为本地 `.env`（已被 `.gitignore`，不会提交）。

## 约束与定位

- 纯标准库，无第三方依赖（`sqlite3` / `hashlib` / `json` / `re` / `urllib` / `unittest`）。
- 可离线演示（`FakeLLM`），可接真实 LLM（`DeepSeekLLM`）。
- 这是「最小实现」与可行性验证，不是生产级系统；已知简化见各子系统 README。
