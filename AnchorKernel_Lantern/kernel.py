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
_MAX_SESSIONS = 1000
_SESSION_TTL = 3600


def _load_skill_content() -> str:
    """加载 Skill 文件内容（仅准则主体，过滤开发文档）"""
    try:
        with open(_SKILL_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        lines = content.split("\n")
        # 跳过第一行标题
        if lines and lines[0].startswith("# "):
            lines = lines[1:]

        # 只保留 LLM 需要的章节（简介 / 核心准则 / 触发条件）
        # 丢弃使用方式、已知限制等开发文档
        keep_sections = {"简介", "核心准则", "触发条件"}
        result = []
        current_section = None
        for line in lines:
            if line.startswith("## "):
                section_name = line[2:].strip()
                current_section = section_name
            if current_section is None or current_section in keep_sections:
                result.append(line)

        return "\n".join(result).strip()
    except FileNotFoundError:
        return ""


SKILL_CONTENT = _load_skill_content()

SYSTEM_PROMPT_SUMMARY = "已加载技能：General_Execution_Policy_v1。请严格遵循准则执行。"


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
                f"【技能：{self.skill_name}】\n\n"
                f"{self._skill_content}\n\n"
                f"每轮请关注 [⚡准则锚点：按初始准则执行]。"
            )
        return SYSTEM_PROMPT_SUMMARY

    def build_payload(
        self,
        user_input: str,
        history_messages: List[Dict[str, Any]],
        is_first_turn: bool = False,
        session_id: Optional[str] = None,
        keep_clean: bool = True,
    ) -> Dict[str, Any]:
        """
        构建每次 LLM 调用的 payload

        Args:
            user_input: 用户原始输入
            history_messages: 消息历史列表（应为历史中干净的消息）
            is_first_turn: 是否为首轮（手动模式，与 session_id 二选一）
            session_id: 会话 ID（自动模式，推荐使用）
            keep_clean: True（默认）- messages 存原文，anchor 字段独立携带，
                        送给 LLM 前需调用 apply_anchor() 追加后缀。
                        False - 旧行为，anchor 直接写进 content（向后兼容）。

        Returns:
            {
                "messages": [...],              # 处理后的消息列表
                "messages_clean": [...],        # 仅在 keep_clean=True 时返回，内容同 messages（用户原文干净）
                "messages_for_llm": [...],      # 仅在 keep_clean=True 时返回，已追加锚点的版本
                "anchor": str,                  # 本轮使用的锚点
                "is_first_turn": bool,
                "turn_count": int,
            }
        """
        now = time.time()

        with self._lock:
            if session_id is not None:
                self._cleanup_sessions()
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

        messages = deepcopy(history_messages)

        if is_first:
            messages = [m for m in messages if m.get("role") != "system"]
            messages.insert(0, {"role": "system", "content": self._build_system_prompt()})

        anchor = self.ANCHOR_SUFFIX
        if is_first:
            anchor = self.FIRST_TURN_SUFFIX + self.ANCHOR_SUFFIX

        if keep_clean:
            # 新行为：messages 存原文（干净），锚点独立携带
            clean_messages = deepcopy(messages)
            clean_messages.append({"role": "user", "content": user_input})

            # LLM 版本：临时追加锚点（不污染原始 messages）
            llm_messages = deepcopy(messages)
            llm_messages.append({"role": "user", "content": user_input + anchor})

            return {
                "messages": llm_messages,  # 向后兼容：默认仍返回带锚点的版本
                "messages_clean": clean_messages,
                "messages_for_llm": llm_messages,
                "anchor": anchor,
                "is_first_turn": is_first,
                "turn_count": turn_count + 1 if turn_count >= 0 else -1,
            }
        else:
            # 旧行为：anchor 直接写进 content（向后兼容）
            messages.append({"role": "user", "content": user_input + anchor})
            return {
                "messages": messages,
                "anchor": anchor,
                "is_first_turn": is_first,
                "turn_count": turn_count + 1 if turn_count >= 0 else -1,
            }

    def apply_anchor(
        self,
        messages: List[Dict[str, Any]],
        anchor: str,
    ) -> List[Dict[str, Any]]:
        """
        将锚点追加到 messages 中最后一条 user 消息的 content。
        用于 keep_clean=True 时，在「送给 LLM 前」临时追加后缀，
        而不污染原始 messages（用于存档/历史）。
        """
        messages = deepcopy(messages)
        for i in range(len(messages) - 1, -1, -1):
            if messages[i].get("role") == "user":
                messages[i]["content"] = messages[i]["content"] + anchor
                break
        return messages

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
    keep_clean: bool = True,
) -> Dict[str, Any]:
    """便捷函数：构建 payload"""
    return get_kernel().build_payload(user_input, history_messages, is_first_turn, session_id, keep_clean)
