"""家庭资产：手工资产/负债项 + 盘点快照（PRD M6）。

- 投资持仓不在此表：由原「攒息」的 holdings/lots 自动汇总（asset_service 读现有能力）；
- 快照只在用户主动「盘点」时生成 —— 自动快照会让趋势被当日行情污染（PRD §M6）。
"""
from typing import Optional

from sqlmodel import Field, SQLModel

from ..utils.timeutil import now_str


class AssetItem(SQLModel, table=True):
    __tablename__ = "asset_items"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    category: str = Field(index=True)   # cash 现金存款 / property 房产 / vehicle 车辆 / other 其他 / liability 负债
    sub_category: Optional[str] = None  # 子类：现金=活期/定期；房产=自住/投资；负债=房贷/车贷/消费贷/其他
    name: str                           # 名称
    amount: float = Field(default=0)    # 金额（负债为正数余额，计算时做减项）
    currency: str = Field(default="CNY")  # CNY / USD / HKD
    note: Optional[str] = None
    repay_date: Optional[str] = None    # 负债还款日（可一键生成一个「日子」条目）
    status: str = Field(default="normal", index=True)  # normal / deleted
    deleted_at: Optional[str] = None
    created_at: str = Field(default_factory=now_str)
    updated_at: str = Field(default_factory=now_str)


class AssetSnapshot(SQLModel, table=True):
    __tablename__ = "asset_snapshots"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    snapshot_date: str = Field(index=True)  # 盘点日期 YYYY-MM-DD
    total_assets: float = Field(default=0)
    total_liabilities: float = Field(default=0)
    net_worth: float = Field(default=0)
    detail: Optional[str] = None            # 当次盘点明细 JSON（仅展示用，不参与计算）
    created_at: str = Field(default_factory=now_str)
