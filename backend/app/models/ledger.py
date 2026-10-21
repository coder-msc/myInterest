"""ledger_records 账本流水表（PRD M2）。金额一律正数，收支方向由 direction 表达。"""
from typing import Optional

from sqlmodel import Field, SQLModel

from ..utils.timeutil import now_str


class LedgerRecord(SQLModel, table=True):
    __tablename__ = "ledger_records"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    direction: str = Field(default="expense", index=True)  # expense 支出 / income 收入
    amount: float = Field(default=0)          # 金额（正数，最多 2 位小数）
    category: str = Field(default="其他", index=True)  # 分类名（预置或自定义）
    account: Optional[str] = None             # 账户：现金/微信/支付宝/银行卡/其他
    occurred_on: str = Field(index=True)      # 发生日期 YYYY-MM-DD（不可未来）
    note: Optional[str] = None                # 备注（≤50 字）
    media_id: Optional[int] = None            # 小票照片 media_assets.id（最多 1 张）
    status: str = Field(default="normal", index=True)  # normal / deleted
    deleted_at: Optional[str] = None
    created_at: str = Field(default_factory=now_str)
    updated_at: str = Field(default_factory=now_str)


class LedgerCategory(SQLModel, table=True):
    """账本分类：预置分类懒创建，自定义分类最多 20 个。

    last_used_at 同时承担「默认选中上一次使用的分类」的实现（按最近使用排序）。
    """
    __tablename__ = "ledger_categories"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    name: str = Field(index=True)
    emoji: str = Field(default="📦")
    is_preset: int = Field(default=0)         # 1=预置（不可删） / 0=自定义
    sort: int = Field(default=0)
    last_used_at: Optional[str] = None
    created_at: str = Field(default_factory=now_str)
