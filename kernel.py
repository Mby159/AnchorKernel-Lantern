"""
AnchorKernel · Lantern
Agent 执行准则核心类
通过 System Prompt 会话级初始化 + User 消息轮次级后缀锚定 实现准则强化
"""

import os
import time
import threading
from copy import deepcopy
from typing import List, Dict, Any, Optional

# Skill 文件的路径（相对本文件）
_SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
_SKILL_PATH = os.path.join(_SKILL_DIR, "skill", "General_Execution_Policy_v1.md")

# 会话清理阈值
_MAX_SESSIONS = 1000      # 最多维护这么多会话，超出后清理最老的
_SESSION_TTL = 3600       # 会话 TTL（秒），超时后自动清理


def _load_skill_content() -> str:
    """加载 Skill 文件内容"""
    try:
        with open(_SKILL_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        lines = content.split("\n")
        if lines and lines[0].startswith("# "):
            lines = lines[1:]
        return "\n".join(lines).strip()
    except FileNotFoundError:
        return ""


SKILL_CONTENT = _load_skill_content()

SYSTEM_PROMPT_SUMMARY = (
    "你是一个高性能执行Agent。已加载技能：General_Execution_Policy_v1。\n"
    "红线：1.禁幻觉 2.用户优先（软冲突） 3.优先结构化输出。\n"
    "后续每轮对话请关注 [⚡准则锚点] 提示。"
)


class AgentKernel:
    """
    Agent 执行准则强化内核

    支持两种模式：
    - 自动模式（推荐）：传入 session_id，内核自动维护 turn 状态
    - 手动模式：传入 is_first_turn，自己维护会话状态
    """

    ANCHOR_SUFFIX = " [⚡准则锚点：按初始准则执行]"
    FIRST_TURN_SUFFIX = " [⚡首次加载准则]"

    def __init__(
        self,
        skill_name: str = "General_Execution_Policy_v1",
        skill_content: Optional[str] = None,
        max_sessions: int = _MAX_SESSIONS,
        session_ttl: int = _SESSION_TTL,
    ):
        self.skill_name = skill_name
        self._skill_content = skill_content or SKILL_CONTENT
        # session_id -> {"turn": int, "last_active": float (timestamp)}
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._max_sessions = max_sessions
        self._session_ttl = session_ttl
        self._lock = threading.Lock()

    def _cleanup_sessions(self) -> None:
        """清理过期会话（超过 TTL 或超过最大数量）"""
        now = time.time()
        expired = [
            sid for sid, info in self._sessions.items()
            if now - info["last_active"] > self._session_ttl
        ]
        for sid in expired:
            del self._sessions[sid]

        # 超出上限，清理最老的
        if len(self._sessions) > self._max_sessions:
            sorted_sessions = sorted(
                self._sessions.items(),
                key=lambda x: x[1]["last_active"]
            )
            for sid, _ in sorted_sessions[:len(self._sessions) - self._max_sessions]:
                del self._sessions[sid]

    def _build_system_prompt(self) -> str:
        """构建完整的 system prompt（包含 Skill 全文）"""
        if self._skill_content:
            return (
                f"【技能加载：{self.skill_name}】\n\n"
                f"{self._skill_content}\n\n"
                f"——\n"
                f"请严格遵循上述准则执行。\n"
                f"每轮对话请关注 [⚡准则锚点：按初始准则执行] 提示。"
            )
        return SYSTEM_PROMPT_SUMMARY

    def build_payload(
        self,
        user_input: str,
        history_messages: List[Dict[str, Any]],
        is_first_turn: bool = False,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        构建每次 LLM 调用的 payload

        Args:
            user_input: 用户原始输入
            history_messages: 消息历史列表
            is_first_turn: 是否为首轮（手动模式，与 session_id 二选一）
            session_id: 会话 ID（自动模式，推荐使用）

        Returns:
            {
                "messages": [...],          # 处理后的消息列表
                "anchor": str,              # 常规锚点
                "anchor_for_first_turn": str, # 首轮锚点（含首次加载标记）
                "is_first_turn": bool,
                "turn_count": int,
            }
        """
        now = time.time()

        with self._lock:
            if session_id is not None:
                self._cleanup_sessions()  # 入锁前先清理
                info = self._sessions.get(session_id)
                if info is None:
                    turn_count = 0
                    is_first = True
                else:
                    turn_count = info["turn"]
                    is_first = False
                self._sessions[session_id] = {
                    "turn": turn_count + 1,
                    "last_active": now,
                }
            else:
                is_first = is_first_turn
                turn_count = -1

        # 深拷贝，避免修改原始消息对象
        messages = deepcopy(list(history_messages))

        if is_first:
            messages = [m for m in messages if m.get("role") != "system"]
            messages.insert(0, {"role": "system", "content": self._build_system_prompt()})

        anchor = self.ANCHOR_SUFFIX
        if is_first:
            anchor = self.FIRST_TURN_SUFFIX + self.ANCHOR_SUFFIX

        # 直接追加新的 user 消息（锚点追加到 content 是为了向后兼容）
        # 注：如需原文干净，调用方应使用返回的 anchor 字段自行处理，
        # messages 中追加的是 user_input + anchor（向后兼容模式）。
        messages.append({"role": "user", "content": user_input + anchor})

        return {
            "messages": messages,
            "anchor": self.ANCHOR_SUFFIX,
            "anchor_for_first_turn": self.FIRST_TURN_SUFFIX + self.ANCHOR_SUFFIX,
            "is_first_turn": is_first,
            "turn_count": turn_count + 1 if turn_count >= 0 else -1,
        }

    def get_anchor(self, is_first_turn: bool = False) -> str:
        """仅获取锚点字符串（不处理 messages）"""
        if is_first_turn:
            return self.FIRST_TURN_SUFFIX + self.ANCHOR_SUFFIX
        return self.ANCHOR_SUFFIX

    def reset_session(self, session_id: str) -> None:
        """重置指定会话的状态"""
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]


# ==================== 便捷函数 ====================

_kernel: Optional[AgentKernel] = None
_kernel_lock = threading.Lock()


def get_kernel() -> AgentKernel:
    global _kernel
    if _kernel is None:
        with _kernel_lock:
            if _kernel is None:
                _kernel = AgentKernel()
    return _kernel


def build_payload(
    user_input: str,
    history_messages: List[Dict[str, Any]],
    is_first_turn: bool = False,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """便捷函数：构建 payload"""
    return get_kernel().build_payload(user_input, history_messages, is_first_turn, session_id)
