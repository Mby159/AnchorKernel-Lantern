# AnchorKernel · Lantern

> 众里寻他千百度，蓦然回首，那人却在灯火阑珊处。

极简、无侵入、低成本的 Agent 执行准则强化内核。

## 安装

```bash
pip install anchor-kernel-lantern
```

或开发模式：

```bash
git clone https://github.com/Mby159/AnchorKernel-Lantern.git
cd AnchorKernel-Lantern
pip install -e .
```

## 目录结构

```
AnchorKernel_Lantern/           # 注意：目录名含连字符，Python 包名为 anchor_kernel_lantern
├── AnchorKernel_Lantern/       # Python 包（含 __init__.py）
│   ├── __init__.py
│   ├── kernel.py
│   └── skill/
│       └── General_Execution_Policy_v1.md
├── example.py                  # 使用示例
├── pyproject.toml
└── README.md
```

> ⚠️ 仓库目录名为 `AnchorKernel-Lantern`（连字符），但 Python 包名不允许连字符。
> 安装后包名为 `anchor_kernel_lantern`，import 时用 `from anchor_kernel_lantern import AgentKernel`。

## 快速开始

```python
from anchor_kernel_lantern import AgentKernel

kernel = AgentKernel()

# 方式一：自动模式（推荐）- 传入 session_id，自动维护 turn 状态
payload = kernel.build_payload(
    user_input="用户输入",
    history_messages=[],
    session_id="unique-session-id"
)
# messages_for_llm 追加了锚点，送 LLM 用这个
# messages_clean 原文干净，用于存档
llm_messages = payload["messages_for_llm"]
clean_archive = payload["messages_clean"]

# 方式二：手动模式
payload = kernel.build_payload(
    user_input="用户输入",
    history_messages=messages,
    is_first_turn=False
)
```

### 发送给 LLM vs 存档（重要）

```
history（下一轮传入 + 存档）  ←── 始终用 messages_clean
送 LLM                       ←── 用 messages_for_llm，或 apply_anchor(history, anchor)
```

> ⚠️ `messages_for_llm` 是"投递版"——用完即弃，不能作 history。
> `messages_clean` 是"记忆版"——持续流动，始终干净。

```python
payload = kernel.build_payload("用户输入", history_messages, session_id="chat")

# 送给 LLM（追加了锚点）
llm_messages = payload["messages_for_llm"]

# 存档（原文干净，无锚点污染）
archive = payload["messages_clean"]

# 下轮对话：history 用 messages_clean；messages_for_llm 仅在送 LLM 那一刻用
history = archive
```

### 自行追加锚点（apply_anchor）

如果调用方想完全控制锚点追加时机：

```python
payload = kernel.build_payload("用户输入", history, session_id="chat", keep_clean=True)

# 存档用 messages_clean（干净）
archive = payload["messages_clean"]

# 送 LLM 前，手动 apply_anchor
llm = kernel.apply_anchor(archive, payload["anchor"])
```

## 核心机制

| 机制 | 时机 | 内容 |
|------|------|------|
| System Prompt | 仅首轮 | 完整 Skill 内容拼入 |
| User 锚点 | 送 LLM 前 | `[⚡准则锚点：按初始准则执行]` |
| 原文存档 | 全程 | messages_clean 保持干净 |

## 关键设计：双轨消息

`keep_clean=True`（默认）时，`build_payload` 返回三个消息列表：

- `messages`（向后兼容）：等于 `messages_for_llm`
- `messages_for_llm`：最后一条 user 追加了锚点，送 LLM 用
- `messages_clean`：最后一条 user 是原文，存档用

这样对话历史始终干净，锚点只在「送给 LLM 的那一瞬间」生效。

## 对接框架

### Dify / Coze
在 LLM 节点前放一个 Code Node，使用 `build_payload` 处理。

### LangChain
封装为 `RunnableLambda`，插入 LCEL 链。

### 原生 OpenAI SDK
每次 `client.chat.completions.create` 前调用。

## 注意：assistant 回复需要调用方自行追加

`build_payload` 只负责处理 user 消息和 system prompt。
多轮对话时，assistant 回复需要调用方自行追加到 history：

```python
history = []

for turn in range(1, 6):
    payload = kernel.build_payload(f"第{turn}轮", history, session_id="chat")

    # 送给 LLM 用 messages_for_llm（已追加锚点）
    llm_messages = payload["messages_for_llm"]

    # --- 这里调用 LLM ---
    # response = llm.chat(llm_messages)

    # 模拟 assistant 回复（追加到 history，不是 llm_messages）
    llm_messages.append({"role": "assistant", "content": "Agent 回复"})

    # 下轮 history 用 messages_clean（始终干净）
    # messages_for_llm 是"投递版"用完即弃，不能作 history
    history = payload["messages_clean"]
```

## 已知限制

1. **手动模式首轮判定**：依赖调用方传入正确的 `is_first_turn`，建议用 `session_id` 自动模式。
2. **keep_clean=False 时仍有污染**：设为 False 则 anchor 写进 content，向后兼容但会污染历史。

## 运行示例

```bash
pip install -e .
python -m anchor_kernel_lantern.example
```
