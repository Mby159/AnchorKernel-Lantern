"""
AnchorKernel · Lantern 使用示例
"""

from AnchorKernel_Lantern import AgentKernel


def demo_basic():
    """基础用法演示（默认 keep_clean=True）"""
    kernel = AgentKernel()

    print("=" * 50)
    print("【首轮对话 - 默认行为（messages_clean）】")
    payload = kernel.build_payload("今天天气怎么样？", [], session_id="basic-1")

    print(f"messages_clean（存档用，原文干净）:")
    for msg in payload["messages_clean"]:
        content = msg["content"]
        if len(content) > 80:
            content = content[:80] + "..."
        print(f"  [{msg['role']}]: {content}")

    print(f"\nmessages_for_llm（送 LLM，追加锚点）:")
    for msg in payload["messages_for_llm"]:
        content = msg["content"]
        if len(content) > 80:
            content = content[:80] + "..."
        print(f"  [{msg['role']}]: {content}")


def demo_long_conversation():
    """长对话：验证历史消息干净"""
    print("\n" + "=" * 50)
    print("【长对话 - 历史消息干净】")

    kernel = AgentKernel()
    # 关键：history 始终用 messages_clean（干净版），messages_for_llm 只在送 LLM 那一刻用
    history = []

    for turn in range(1, 4):
        payload = kernel.build_payload(
            f"第{turn}轮输入",
            history_messages=history,
            session_id="long-chat"  # 固定 session_id，turn 正常累加
        )

        # 送 LLM 用 messages_for_llm（已追加锚点）
        llm_messages = payload["messages_for_llm"]

        # 模拟 assistant 回复（追加到 history，不是 llm_messages）
        # llm_messages 是"投递版"用完即弃，assistant 要持久化进 history
        history = payload["messages_clean"]
        history.append({"role": "assistant", "content": f"Agent 第{turn}轮回复"})

        print(f"Turn {turn}: is_first={payload['is_first_turn']}, turn_count={payload['turn_count']}")

    # 验证历史干净
    print(f"\n历史消息中所有 user 消息（应为干净原文）：")
    for m in history:
        if m["role"] == "user":
            print(f"  - {m['content']}")

    # 验证存档无锚点
    anchors_in_archive = any("⚡" in m["content"] for m in history if m["role"] == "user")
    print(f"\n存档中是否有锚点污染: {'是 ❌' if anchors_in_archive else '无 ✅'}")


def demo_apply_anchor():
    """apply_anchor：送给 LLM 前临时追加锚点"""
    print("\n" + "=" * 50)
    print("【apply_anchor 临时追加锚点】")

    kernel = AgentKernel()

    payload = kernel.build_payload(
        "别用JSON了，直接说人话",
        [],
        is_first_turn=True,
        keep_clean=True,
    )

    # 存档用 messages_clean（干净）
    archive = payload["messages_clean"]
    print(f"存档: {[m['content'] for m in archive if m['role']=='user']}")

    # 送 LLM 前，手动用 apply_anchor
    llm = kernel.apply_anchor(archive, payload["anchor"])
    print(f"送LLM: {[m['content'] for m in llm if m['role']=='user']}")


def demo_keep_clean_false():
    """keep_clean=False：旧行为（向后兼容）"""
    print("\n" + "=" * 50)
    print("【keep_clean=False 旧行为】")

    kernel = AgentKernel()

    payload = kernel.build_payload(
        "测试旧行为",
        [],
        is_first_turn=True,
        keep_clean=False,
    )

    print(f"user content: {payload['messages'][-1]['content']}")
    print("(锚点直接写进 content，向后兼容)")


def demo_auto_mode():
    """自动模式 - session_id 自动维护 turn"""
    print("\n" + "=" * 50)
    print("【自动模式 - session_id】")

    kernel = AgentKernel()

    for i in range(1, 4):
        payload = kernel.build_payload(
            f"第{i}轮",
            [],
            session_id="auto-1"
        )
        print(f"Turn {payload['turn_count']}: is_first={payload['is_first_turn']}")

    print("\n--- 新会话 ---")
    payload = kernel.build_payload("新会话首轮", [], session_id="auto-2")
    print(f"Turn {payload['turn_count']}: is_first={payload['is_first_turn']}")


def demo_session_management():
    """会话管理 - reset_session"""
    print("\n" + "=" * 50)
    print("【会话管理】")

    kernel = AgentKernel()

    p1 = kernel.build_payload("输入", [], session_id="session-a")
    print(f"session-a turn1: {p1['turn_count']}")

    p2 = kernel.build_payload("输入", [], session_id="session-a")
    print(f"session-a turn2: {p2['turn_count']}")

    kernel.reset_session("session-a")
    p3 = kernel.build_payload("输入", [], session_id="session-a")
    print(f"session-a after reset: turn={p3['turn_count']}, is_first={p3['is_first_turn']}")


def demo_hallucination_prevention():
    """防幻觉场景"""
    print("\n" + "=" * 50)
    print("【防幻觉场景】")

    kernel = AgentKernel()

    payload = kernel.build_payload(
        "根据2024年Q3财报，公司营收是多少？",
        [],
        is_first_turn=True,
    )

    user_msg = payload["messages_for_llm"][-1]["content"]
    print(f"用户消息: {user_msg}")
    print("→ Agent 应回复「资料不足，无法确认」")


if __name__ == "__main__":
    demo_basic()
    demo_long_conversation()
    demo_apply_anchor()
    demo_keep_clean_false()
    demo_auto_mode()
    demo_session_management()
    demo_hallucination_prevention()
