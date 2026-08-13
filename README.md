# AnchorKernel · Lantern

> 众里寻他千百度，蓦然回首，那人却在灯火阑珊处。

极简、无侵入、低成本的 Agent 执行准则强化内核。

## 目录结构

```
AnchorKernel_Lantern/
├── __init__.py          # 包入口
├── kernel.py            # 核心 AgentKernel 类
├── example.py           # 使用示例
├── README.md            # 本文件
└── skill/
    └── General_Execution_Policy_v1.md   # 执行准则 Skill（完整内容注入 System Prompt）
```

## 快速开始

```python
from AnchorKernel_Lantern import AgentKernel

kernel = AgentKernel()

# 方式一：自动模式（推荐）—— 传入 session_id，自动维护 turn 状态
payload = kernel.build_payload(
    user_input="用户输入",
    history_messages=[],
    session_id="unique-session-id"
)
anchor = payload["anchor"]  # 锚点独立携带，可自行决定如何附加

# 方式二：手动模式 —— 自行维护 is_first_turn
payload = kernel.build_payload(
    user_input="用户输入",
    history_messages=messages,
    is_first_turn=False
)

messages = payload["messages"]
```

## 核心机制

| 机制 | 时机 | 内容 |
|------|------|------|
| System Prompt | 仅首轮 | 完整 Skill 内容拼入，约 200 字 |
| User 后缀 | 每轮 | 约 12 字，`[⚡准则锚点：按初始准则执行]` |
| 双重后缀 | 首轮用户 | `首轮额外后缀 + 锚点后缀` |

## 关键特性

### Skill 内容对 LLM 可见
`General_Execution_Policy_v1.md` 的完整内容会在首轮拼入 System Prompt，
LLM 实际看到的是完整的 5 条准则，而非仅一个名字。

### 锚点独立携带
`build_payload` 返回的 payload 中包含独立的 `anchor` 字段，
如需原文干净（存档/敏感词过滤场景），可自行决定如何附加。

### 自动 turn 状态
传入 `session_id` 后，内核自动维护会话状态，无需自行判断首轮。

## 对接框架

### Dify / Coze
在 LLM 节点前放一个 Code Node，使用 `build_payload` 处理。

### LangChain
封装为 `RunnableLambda`，插入 LCEL 链。

### 原生 OpenAI SDK
每次 `client.chat.completions.create` 前调用。

## 已知限制

1. **后缀污染**：当前版本将锚点追加到 user 消息 content 中，
   如需原文干净（用于存档/敏感词过滤），请使用 `get_anchor()` 自行附加。
2. **首轮判定**：手动模式下依赖调用方传入正确的 `is_first_turn`，
   建议使用 `session_id` 自动模式以避免错误。

## 运行示例

```bash
cd AnchorKernel_Lantern
python example.py
```
