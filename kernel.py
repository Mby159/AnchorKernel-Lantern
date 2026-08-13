"""
Agent 执行准则核心类
通过 System Prompt 会话级初始化 + User 消息轮次级后缀锚定 实现准则强化
"""

from typing import List, Dict, Any, Optional


class AgentKernel:
    """Agent 执行准则强化内核"""

    SYSTEM_PROMPT = (
        "你是一个高性能执行Agent。已加载技能：General_Execution_Policy_v1。\n"
        "红线：1.禁幻觉 2.用户优先（软冲突） 3.优先结构化输出。\n"
        "后续每轮对话请关注 [⚡准则锚点] 提示。"
    )

    ANCHOR_SUFFIX = " [⚡准则锚点：按初始准则执行]"
    FIRST_TURN_SUFFIX = " [⚡首次加载准则]"

    def __init__(self, skill_name: str = "General_Execution_Policy_v1"):
        self.skill_name = skill_name

    def build_payload(
        self,
        user_input: str,
        history_messages: List[Dict[str, Any]],
        is_first_turn: bool = False,
    ) -> Dict[str, Any]:
        """
        构建每次 LLM 调用的 payload

        Args:
            user_input: 用户原始输入
            history_messages: 消息历史列表 (含 role/content)
            is_first_turn: 是否为首轮对话

        Returns:
            处理后的 payload dict
        """
        messages = [msg.copy() for msg in history_messages]

        if is_first_turn:
            # 清除旧 System（仅首次注入）
            messages = [m for m in messages if m.get("role") != "system"]
            # 插入新 System
            messages.insert(0, {"role": "system", "content": self.SYSTEM_PROMPT})
            # 首轮 User 加双重后缀
            processed_input = user_input + self.FIRST_TURN_SUFFIX + self.ANCHOR_SUFFIX
        else:
            # 后续轮次：只加锚点后缀
            processed_input = user_input + self.ANCHOR_SUFFIX

        # 替换最后一条 user 消息的 content
        replaced = False
        for i in range(len(messages) - 1, -1, -1):
            if messages[i].get("role") == "user":
                messages[i]["content"] = processed_input
                replaced = True
                break

        if not replaced:
            # 异常情况：没有 user 消息，直接追加
            messages.append({"role": "user", "content": processed_input})

        return {"messages": messages}

    def inject_system_prompt(
        self, history_messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        仅注入 System Prompt（不处理 user 消息），用于首轮独立调用
        """
        messages = [msg.copy() for msg in history_messages]
        messages = [m for m in messages if m.get("role") != "system"]
        messages.insert(0, {"role": "system", "content": self.SYSTEM_PROMPT})
        return messages

    def append_anchor(
        self, user_input: str, is_first_turn: bool = False
    ) -> str:
        """
        仅拼接后缀（不处理 history），用于框架已处理 history 的场景
        """
        if is_first_turn:
            return user_input + self.FIRST_TURN_SUFFIX + self.ANCHOR_SUFFIX
        return user_input + self.ANCHOR_SUFFIX


# ==================== 便捷函数 ====================

_kernel: Optional[AgentKernel] = None


def get_kernel() -> AgentKernel:
    """获取单例 kernel 实例"""
    global _kernel
    if _kernel is None:
        _kernel = AgentKernel()
    return _kernel


def build_payload(
    user_input: str,
    history_messages: List[Dict[str, Any]],
    is_first_turn: bool = False,
) -> Dict[str, Any]:
    """便捷函数：构建 payload"""
    return get_kernel().build_payload(user_input, history_messages, is_first_turn)


def append_anchor(user_input: str, is_first_turn: bool = False) -> str:
    """便捷函数：追加锚点后缀"""
    return get_kernel().append_anchor(user_input, is_first_turn)
