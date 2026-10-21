"""life_events 足迹·人生大事件表（PRD M4）。照片走 media_assets(owner_type='event')。

与旅游的区别：旅游是「一段时间」，大事件是「一个时刻」。事件日期允许选未来。
"""
from typing import Optional

from sqlmodel import Field, SQLModel

from ..utils.timeutil import now_str


class LifeEvent(SQLModel, table=True):
    __tablename__ = "life_events"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    title: str                                    # 标题（≤30 字）
    event_date: str = Field(index=True)           # 日期 YYYY-MM-DD（可未来）
    category: str = Field(default="里程碑", index=True)  # 工作/学业/家庭/健康/财务/里程碑/自定义
    emoji: str = Field(default="🎉")              # 类型 emoji（自定义类型自带）
    mood: Optional[str] = None                    # 心情 emoji（不参与统计）
    content: Optional[str] = None                 # 正文（≤2000 字）
    tags: Optional[str] = None                    # 标签 JSON 数组（最多 5 个）
    status: str = Field(default="normal", index=True)  # normal / deleted
    deleted_at: Optional[str] = None
    created_at: str = Field(default_factory=now_str)
    updated_at: str = Field(default_factory=now_str)
