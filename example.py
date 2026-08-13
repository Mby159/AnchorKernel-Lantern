"""
AnchorKernel · Lantern 使用示例
"""

from AnchorKernel_Lantern import AgentKernel


def demo_basic():
    """基础用法演示（手动模式）"""
    kernel = AgentKernel()

    # === 首轮对话 ===
    print("=" * 50)
    print("【首轮对话 - 手动模式】")
    payload = kernel.build_payload("今天天气怎么样？", history_messages=[], is_first_turn=True)

    for msg in payload["messages"]:
        content = msg["content"]
        if len(content) > 100:
            content = content[:100] + "..."
        print(f"[{msg['role']}]: {content}")

    # === 后续对话 ===
    print("\n" + "=" * 50)
    print("【第2轮对话】")
    payload2 = kernel.build_payload(
        "那明天呢？",
        history_messages=payload["messages"],
        is_first_turn=False,
    )

    for msg in payload2["messages"]:
        content = msg["content"]
        if len(content) > 100:
            content = content[:100] + "..."
        print(f"[{msg['role']}]: {content}")


def demo_auto_mode():
    """自动模式演示 - session_id 自动维护 turn 状态"""
    print("\n" + "=" * 50)
    print("【自动模式 - session_id】")

    kernel = AgentKernel()

    # 同一 session_id 会自动累加 turn
    for i in range(1, 4):
        payload = kernel.build_payload(
            f"第{i}轮输入",
            history_messages=[],
            session_id="chat-001"  # 固定 session_id
        )
        print(f"Turn {payload['turn_count']}: is_first={payload['is_first_turn']}")

    # 新 session_id 会重新从首轮开始
    print("\n--- 新会话 ---")
    payload = kernel.build_payload("新会话首轮", [], session_id="chat-002")
    print(f"Turn {payload['turn_count']}: is_first={payload['is_first_turn']}")


def demo_get_anchor():
    """锚点独立使用 - 原文干净场景"""
    print("\n" + "=" * 50)
    print("【锚点独立使用 - 原文干净】")

    kernel = AgentKernel()

    # 场景：存档/敏感词过滤需要用户原文干净
    original_input = "别用JSON了，直接说人话"

    # 方式一：用 get_anchor() 自己拼接
    anchor = kernel.get_anchor(is_first_turn=True)
    clean_for_llm = original_input + anchor  # 仅送给 LLM
    archive_storage = original_input           # 原文存档，不带锚点

    print(f"原文存档: {archive_storage}")
    print(f"送给LLM: {clean_for_llm}")

    # 方式二：用 build_payload 返回的 anchor 字段
    payload = kernel.build_payload(original_input, [], session_id="clean-demo")
    print(f"\n返回的 anchor: {payload['anchor_for_first_turn']}")
    print(f"messages里的content（向后兼容）: {payload['messages'][-1]['content']}")


def demo_long_conversation():
    """模拟长对话（20+ 轮）- 验证 System 仅首轮注入"""
    print("\n" + "=" * 50)
    print("【长对话模拟 - 前5轮】")

    kernel = AgentKernel()
    messages = []

    for turn in range(1, 6):
        payload = kernel.build_payload(
            f"用户第{turn}轮输入",
            history_messages=messages,
            session_id="long-chat"  # 固定 session_id，同一会话累加 turn
        )
        messages = payload["messages"]

        # 模拟 assistant 回复
        messages.append({
            "role": "assistant",
            "content": f"Agent 第{turn}轮回复：感谢您的提问。",
        })

        print(f"Turn {turn}: is_first={payload['is_first_turn']}, system_count={sum(1 for m in messages if m['role']=='system')}")

    # 验证 System 仅在首轮存在
    system_count = sum(1 for m in messages if m['role'] == 'system')
    print(f"\nSystem 消息数量: {system_count} (应为 1)")


def demo_session_management():
    """会话管理 - 重置、自动清理"""
    print("\n" + "=" * 50)
    print("【会话管理】")

    kernel = AgentKernel()

    # 正常会话
    p1 = kernel.build_payload("输入", [], session_id="session-a")
    print(f"session-a turn1: {p1['turn_count']}")

    p2 = kernel.build_payload("输入", [], session_id="session-a")
    print(f"session-a turn2: {p2['turn_count']}")

    # 手动重置
    kernel.reset_session("session-a")
    p3 = kernel.build_payload("输入", [], session_id="session-a")
    print(f"session-a after reset: turn={p3['turn_count']}, is_first={p3['is_first_turn']}")


def demo_hallucination_prevention():
    """防幻觉场景 - 锚点触发"""
    print("\n" + "=" * 50)
    print("【防幻觉场景】")

    kernel = AgentKernel()

    payload = kernel.build_payload(
        "根据2024年Q3财报，公司营收是多少？",
        history_messages=[],
        is_first_turn=True,
    )

    user_msg = payload["messages"][-1]["content"]
    print(f"用户消息: {user_msg}")
    print("→ Agent 应回复「资料不足，无法确认」")


if __name__ == "__main__":
    demo_basic()
    demo_auto_mode()
    demo_get_anchor()
    demo_long_conversation()
    demo_session_management()
    demo_hallucination_prevention()
