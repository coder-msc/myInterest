"""reminder_messages 站内消息中心（PRD M9）—— 提醒的唯一可靠通道。

写入幂等：dedup_key 唯一索引（如 "countdown:12:2026-10-20:7"），
同一日子的同一档位在同一天只发一条，重复执行不产生重复消息（PRD §7.2）。
"""
from typing import Optional

from sqlmodel import Field, SQLModel

from ..utils.timeutil import now_str


class ReminderMessage(SQLModel, table=True):
    __tablename__ = "reminder_messages"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    kind: str = Field(default="countdown", index=True)  # countdown 日子提醒 / export 导出完成 / system
    title: str
    content: Optional[str] = None
    ref_type: Optional[str] = None    # 点击跳转的条目类型
    ref_id: Optional[int] = None      # 点击跳转的主表记录 id
    dedup_key: Optional[str] = Field(default=None, index=True)  # 幂等键（同用户内唯一）
    read_at: Optional[str] = None     # 已读时间（空=未读）
    created_at: str = Field(default_factory=now_str, index=True)
