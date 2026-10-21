"""trips 足迹·旅游行程表（PRD M3）。照片走 media_assets(owner_type='trip')。"""
from typing import Optional

from sqlmodel import Field, SQLModel

from ..utils.timeutil import now_str


class Trip(SQLModel, table=True):
    __tablename__ = "trips"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    title: str                                     # 标题（默认「城市 + 起止月日」）
    destinations: str = Field(default="[]")        # 目的地城市 JSON 数组（最多 5 个）
    start_date: str = Field(index=True)            # 开始日期 YYYY-MM-DD
    end_date: str = Field(index=True)              # 结束日期 YYYY-MM-DD（不早于开始）
    companions: Optional[str] = None               # 同行人（自由文本 ≤30 字）
    cover_media_id: Optional[int] = None           # 封面图；空则取照片集第一张
    cost: Optional[float] = None                   # 手工填写的花费
    content: Optional[str] = None                  # 正文（≤1000 字）
    status: str = Field(default="normal", index=True)  # normal / deleted
    deleted_at: Optional[str] = None
    created_at: str = Field(default_factory=now_str)
    updated_at: str = Field(default_factory=now_str)
