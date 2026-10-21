"""countdowns 日子（重要日子倒计时）表（PRD M5）。

重复规则 repeat_rule：once 一次性 / yearly 每年（公历）/ monthly 每月 /
yearly_lunar 每年（农历，本地换算不依赖网络）。

农历字段单独存 lunar_month/lunar_day，卡片上同时展示农历与换算后的公历日期，
让用户能一眼核对（PRD §M5 农历说明）。
"""
from typing import Optional

from sqlmodel import Field, SQLModel

from ..utils.timeutil import now_str


class Countdown(SQLModel, table=True):
    __tablename__ = "countdowns"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    name: str = Field(default="")                    # 名称（≤20 字）
    base_date: str = Field(index=True)               # 首个日期 YYYY-MM-DD（当年的锚点）
    repeat_rule: str = Field(default="once", index=True)  # once/yearly/monthly/yearly_lunar
    lunar_month: Optional[int] = None                # 农历月（1-12）
    lunar_day: Optional[int] = None                  # 农历日（1-30）
    lunar_text: Optional[str] = None                 # 农历原文，如「九月十六」
    remind_offsets: str = Field(default="[7, 0]")    # 提醒档位 JSON 数组（30/7/1/0 天）
    pinned: int = Field(default=0)                   # 置顶（最多 3 个）
    emoji: str = Field(default="🎯")
    color: Optional[str] = None                      # 配色（列表辨识）
    note: Optional[str] = None                       # 备注（≤100 字）
    status: str = Field(default="normal", index=True)  # normal / deleted
    deleted_at: Optional[str] = None
    created_at: str = Field(default_factory=now_str)
    updated_at: str = Field(default_factory=now_str)
