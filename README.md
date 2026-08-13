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
    └── General_Execution_Policy_v1.md   # 执行准则 Skill
```

## 快速开始

```python
from AnchorKernel_Lantern import AgentKernel

kernel = AgentKernel()

# 首轮对话
payload = kernel.build_payload("用户输入", history_messages=[], is_first_turn=True)

# 后续对话
payload = kernel.build_payload("用户输入", history_messages=messages, is_first_turn=False)

# 获取处理后的 messages
messages = payload["messages"]
```

## 核心机制

| 机制 | 时机 | 内容 |
|------|------|------|
| System Prompt | 仅首轮 | 约80字，注入 `messages[0]` |
| User 后缀 | 每轮 | 约12字，`[⚡准则锚点：按初始准则执行]` |
| 双重后缀 | 首轮用户 | `首轮额外后缀 + 锚点后缀` |

## 对接框架

### Dify / Coze
在 LLM 节点前放一个 Code Node，使用 `build_payload` 处理。

### LangChain
封装为 `RunnableLambda`，插入 LCEL 链。

### 原生 OpenAI SDK
每次 `client.chat.completions.create` 前调用。

## 运行示例

```bash
cd AnchorKernel_Lantern
python example.py
```
