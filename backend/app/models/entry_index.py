"""entry_index 条目索引层：手札流 / 全局搜索 / 数据导出清单的唯一数据源。

设计要点（PRD §4.2）：
- 只存公共属性（归属用户、条目类型、发生时间、标题、摘要、封面、标签、主表记录号），
  是「索引」不是「副本」——不回写主表、不参与统计、不计入回收站逻辑；
- 唯一写入路径是「创建/编辑/删除模块记录」，且必须与主表写入在【同一事务】内完成，
  否则会出现「手札流有条目、点进去 404」的脏数据（PRD §4 关键约束）；
- 任何时候都能由各模块主表全量重建（entry_service.rebuild_all）。
"""
from typing import Optional

from sqlmodel import Field, SQLModel

from ..utils.timeutil import now_str


class EntryIndex(SQLModel, table=True):
    __tablename__ = "entry_index"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)  # 归属用户
    entry_type: str = Field(index=True)   # ledger / trip / event / countdown / asset_snapshot
    ref_id: int = Field(index=True)       # 对应模块主表的记录 id
    occurred_at: str = Field(index=True)  # 发生时间 YYYY-MM-DD（时间线排序键，编辑不回填）
    occurred_ts: str = Field(default_factory=now_str)  # 同日内的次级排序键
    title: str                            # 标题（列表主文案）
    summary: Optional[str] = None         # 一行摘要
    cover_media_id: Optional[int] = None  # 封面图 media_assets.id
    tags: Optional[str] = None            # 标签 JSON 数组字符串（参与全局搜索）
    extra: Optional[str] = None           # 展示用附加数据 JSON（如账目金额），只展示不参与统计
    status: str = Field(default="normal", index=True)  # normal / deleted（跟随主表软删除）
    deleted_at: Optional[str] = None
    created_at: str = Field(default_factory=now_str)
    updated_at: str = Field(default_factory=now_str)
