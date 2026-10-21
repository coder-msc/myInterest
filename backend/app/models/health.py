"""值得记 · 健康：生理周期 / 亲密记录 / 睡眠。

隐私红线（与产品定位一致）：
- 三类数据都只在本人账号内可见，不写条目索引、不进手札流、不进回收站；
- 删除即真删，导出时单独成组；
- 亲密记录只保留事实字段（日期、类型、保护措施、备注），不做任何露骨描述。
"""
from typing import Optional

from sqlmodel import Field, SQLModel

from ..utils.timeutil import now_str


class CycleRecord(SQLModel, table=True):
    __tablename__ = "cycle_records"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    start_date: str = Field(index=True)            # 经期开始 YYYY-MM-DD
    end_date: Optional[str] = None                 # 结束日；空=还在进行中
    flow: str = Field(default="medium")            # light / medium / heavy
    symptoms: Optional[str] = None                 # 症状 JSON 数组
    note: Optional[str] = None
    created_at: str = Field(default_factory=now_str)
    updated_at: str = Field(default_factory=now_str)


class IntimacyRecord(SQLModel, table=True):
    __tablename__ = "intimacy_records"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    happen_date: str = Field(index=True)           # YYYY-MM-DD
    happen_time: Optional[str] = None              # HH:MM，可不填
    kind: str = Field(default="partner")           # self / partner / multi
    protection: str = Field(default="na")          # condom / pill / none / na
    note: Optional[str] = None
    created_at: str = Field(default_factory=now_str)
    updated_at: str = Field(default_factory=now_str)


class SleepRecord(SQLModel, table=True):
    __tablename__ = "sleep_records"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    sleep_date: str = Field(index=True)            # 起床那天 YYYY-MM-DD
    bed_time: str                                  # 入睡 HH:MM
    wake_time: str                                 # 起床 HH:MM
    duration_min: int = 0                          # 自动计算，跨午夜按次日
    quality: int = Field(default=3)                # 1-5
    note: Optional[str] = None
    created_at: str = Field(default_factory=now_str)
    updated_at: str = Field(default_factory=now_str)
