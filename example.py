"""
AgentKernel 使用示例
"""

from AnchorKernel_Lantern import AgentKernel


def demo_basic():
    """基础用法演示"""
    kernel = AgentKernel()

    # === 首轮对话 ===
    print("=" * 50)
    print("【首轮对话】")
    payload = kernel.build_payload("今天天气怎么样？", history_messages=[], is_first_turn=True)

    for msg in payload["messages"]:
        print(f"[{msg['role']}]: {msg['content']}")

    # === 后续对话 ===
    print("\n" + "=" * 50)
    print("【第2轮对话】")
    payload2 = kernel.build_payload(
        "那明天呢？",
        history_messages=payload["messages"],
        is_first_turn=False,
    )

    for msg in payload2["messages"]:
        print(f"[{msg['role']}]: {msg['content']}")


def demo_long_conversation():
    """模拟长对话（20+ 轮）"""
    print("\n" + "=" * 50)
    print("【长对话模拟 - 前5轮】")

    kernel = AgentKernel()
    messages = []

    for turn in range(1, 6):
        is_first = turn == 1
        user_input = f"用户第{turn}轮输入"

        payload = kernel.build_payload(user_input, history_messages=messages, is_first_turn=is_first)
        messages = payload["messages"]

        # 模拟 assistant 回复
        messages.append({
            "role": "assistant",
            "content": f"Agent 第{turn}轮回复：感谢您的提问。关于「{user_input}」，我已经理解。",
        })

        print(f"Turn {turn}: user_input = {messages[-2]['content'][:40]}...")

    # 验证 System 仅在首轮存在
    system_count = sum(1 for m in messages if m["role"] == "system")
    print(f"\nSystem 消息数量: {system_count} (应为 1)")


def demo_user_override():
    """用户覆盖格式偏好"""
    print("\n" + "=" * 50)
    print("【用户覆盖格式偏好】")

    kernel = AgentKernel()

    # 模拟用户说"别用JSON了，直接说人话"
    payload = kernel.build_payload(
        "别用JSON了，直接说人话",
        history_messages=[],
        is_first_turn=True,
    )

    user_msg = payload["messages"][-1]["content"]
    print(f"用户消息: {user_msg}")


def demo_hallucination_prevention():
    """防幻觉触发"""
    print("\n" + "=" * 50)
    print("【防幻觉场景】")

    kernel = AgentKernel()

    # 用户询问不存在的信息
    payload = kernel.build_payload(
        "根据2024年Q3财报，公司营收是多少？",
        history_messages=[],
        is_first_turn=True,
    )

    user_msg = payload["messages"][-1]["content"]
    print(f"用户消息: {user_msg}")
    print("\n→ Agent 应回复「资料不足，无法确认」")


if __name__ == "__main__":
    demo_basic()
    demo_long_conversation()
    demo_user_override()
    demo_hallucination_prevention()
