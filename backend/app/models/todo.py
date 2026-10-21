"""todos 待办清单表（值得记 · 待办）。

轻量清单：不写条目索引（避免每日琐事刷屏手札流），不支持照片。
删除即真删——待办是随手记随手清的，不需要回收站。
"""
from typing import Optional

from sqlmodel import Field, SQLModel

from ..utils.timeutil import now_str


class Todo(SQLModel, table=True):
    __tablename__ = "todos"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    title: str                                        # 待办内容（≤60 字）
    note: Optional[str] = None                        # 备注（≤200 字）
    due_date: Optional[str] = Field(default=None, index=True)  # 计划日期 YYYY-MM-DD，空=没定日子
    important: bool = Field(default=False)            # 标为重要：同组内优先展示
    done: bool = Field(default=False, index=True)
    done_at: Optional[str] = None
    created_at: str = Field(default_factory=now_str)
    updated_at: str = Field(default_factory=now_str)
