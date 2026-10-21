"""Pydantic 请求模型（入参白名单校验，docs/04 各接口入参表）。"""
from datetime import date as Date
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

Market = Literal["a_share", "us_stock", "hk_stock", "fund", "bond"]
Currency = Literal["CNY", "USD", "HKD"]
Freq = Literal["monthly", "quarterly", "semi_annual", "annual", "irregular", "unknown"]
# 持仓频率更新专用：除具体频率外允许 "auto"，表示恢复 securities 表的系统推断值
FreqOrAuto = Literal["monthly", "quarterly", "semi_annual", "annual",
                     "irregular", "unknown", "auto"]
Direction = Literal["buy", "sell", "bonus_share"]


# ---------- auth ----------
class RefreshIn(BaseModel):
    refresh_token: str


class WxLoginIn(BaseModel):
    code: str = Field(min_length=1)
    nickname: Optional[str] = None
    avatar: Optional[str] = None


# ---------- auth：邮箱验证码相关 ----------
class SendCodeIn(BaseModel):
    """发送验证码：channel=email/sms，target=邮箱/手机号，purpose=login（登录/注册合一）/bind（绑定邮箱）"""
    channel: Literal["email", "sms"]
    target: str = Field(min_length=4, max_length=64)
    purpose: Literal["login", "bind"]


class EmailLoginIn(BaseModel):
    """邮箱验证码登录：邮箱 + 验证码（未注册自动建号）"""
    email: str = Field(min_length=4)
    code: str = Field(min_length=4, max_length=8)


class ProfileIn(BaseModel):
    """修改个人资料：昵称 / 头像（emoji），至少传一项"""
    nickname: Optional[str] = Field(default=None, max_length=32)
    avatar: Optional[str] = Field(default=None, max_length=32)


class BindEmailIn(BaseModel):
    """绑定邮箱（已登录用户）：邮箱 + 验证码"""
    email: str = Field(min_length=4)
    code: str = Field(min_length=4, max_length=8)


class TestMailIn(BaseModel):
    """后台测试发信：收件邮箱"""
    to: str = Field(min_length=4)


# ---------- holdings ----------
class FirstLotIn(BaseModel):
    trade_date: Date
    shares: float = Field(gt=0)
    price: float = Field(ge=0)
    fee: float = Field(default=0, ge=0)
    note: Optional[str] = None


class HoldingCreate(BaseModel):
    market: Market
    code: str = Field(min_length=1)
    name: str = Field(min_length=1)
    currency: Currency
    account: Optional[str] = None
    freq: Freq = "unknown"
    note: Optional[str] = None
    first_lot: Optional[FirstLotIn] = None


class HoldingUpdate(BaseModel):
    name: Optional[str] = None
    account: Optional[str] = None
    freq: Optional[FreqOrAuto] = None
    note: Optional[str] = None
    currency: Optional[Currency] = None
    current_price: Optional[float] = Field(default=None, ge=0)


# ---------- lots ----------
class LotCreate(BaseModel):
    trade_date: Date
    direction: Direction
    shares: float = Field(gt=0)
    price: float = Field(default=0, ge=0)
    fee: float = Field(default=0, ge=0)
    note: Optional[str] = None


class LotUpdate(BaseModel):
    trade_date: Optional[Date] = None
    direction: Optional[Direction] = None
    shares: Optional[float] = Field(default=None, gt=0)
    price: Optional[float] = Field(default=None, ge=0)
    fee: Optional[float] = Field(default=None, ge=0)
    note: Optional[str] = None


# ---------- batch：批量录入 ----------
class LotBatchIn(BaseModel):
    """批量录入批次：支持一次提交多个买入/卖出/送转记录。"""
    lots: list[LotCreate] = Field(min_length=1, max_length=100)


class ScheduleBatchApproveIn(BaseModel):
    """批量审核预案：发布或驳回多条 pending 预案。"""
    ids: list[int] = Field(min_length=1, max_length=100)
    action: Literal["publish", "reject"]
    reason: Optional[str] = Field(default=None, max_length=200)


# ---------- settings ----------
class SettingsUpdate(BaseModel):
    remind_before_days: Optional[int] = Field(default=None, ge=0, le=30)
    remind_on_payday: Optional[int] = Field(default=None, ge=0, le=1)
    auto_match_schedule: Optional[int] = Field(default=None, ge=0, le=1)
    push_enabled: Optional[int] = Field(default=None, ge=0, le=1)
    wx_subscribe: Optional[int] = Field(default=None, ge=0, le=1)
    # v8：账户元数据与可见币种（JSON 数组字符串，由前端序列化）
    accounts_meta: Optional[str] = None
    visible_currencies: Optional[str] = None


# ---------- schedules（预案，docs/04 §5.3/11.3）----------
class ScheduleAdminCreate(BaseModel):
    market: Market
    code: str = Field(min_length=1, max_length=16)
    name: str = Field(min_length=1, max_length=64)
    ex_date: Optional[Date] = None
    record_date: Optional[Date] = None
    pay_date: Optional[Date] = None
    dps: Optional[float] = Field(default=None, gt=0)
    currency: Currency = "CNY"
    div_type: Literal["cash", "bonus_share"] = "cash"
    raw_title: Optional[str] = None


class ScheduleUserSubmitIn(BaseModel):
    """用户提交预案（docs/04 §5.3）：进入待审核队列，需管理员审核。"""
    market: Market
    code: str = Field(min_length=1, max_length=16)
    name: str = Field(min_length=1, max_length=64)
    ex_date: Optional[Date] = None
    record_date: Optional[Date] = None
    pay_date: Optional[Date] = None
    dps: float = Field(gt=0)
    currency: Currency = "CNY"
    note: Optional[str] = Field(default=None, max_length=200)


class ScheduleRejectIn(BaseModel):
    reason: str = Field(min_length=1, max_length=200)


# ---------- community（公告/反馈，docs/04 §十/11.5/11.6）----------
class FeedbackCreate(BaseModel):
    content: str = Field(min_length=1, max_length=1000)
    contact: Optional[str] = Field(default=None, max_length=100)


class AnnouncementCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1)
    publish: bool = False


class AnnouncementUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=100)
    content: Optional[str] = None
    status: Optional[Literal["draft", "published", "offline"]] = None


class FeedbackHandleIn(BaseModel):
    status: Literal["pending", "adopted", "planned", "done", "rejected"]
    reply: Optional[str] = Field(default=None, max_length=500)


# ---------- admin：汇率/税率（docs/04 §11.4）----------
class RateManualIn(BaseModel):
    base: Literal["USD", "HKD"]
    rate: float = Field(gt=0)
    rate_date: Date


class TaxRuleUpdate(BaseModel):
    rate: Optional[float] = Field(default=None, ge=0, le=1)
    enabled: Optional[int] = Field(default=None, ge=0, le=1)


class ConfigUpdateIn(BaseModel):
    """系统配置批量更新：{配置key: 新值}，敏感项传空串表示不修改。"""
    items: dict[str, Any] = Field(min_length=1)


# ---------- admin：证券管理 ----------
class SecurityCreateIn(BaseModel):
    """后台新增证券（用于维护爬虫白名单）。"""
    market: Market
    code: str = Field(min_length=1, max_length=16)
    name: str = Field(min_length=1, max_length=64)
    currency: Currency = "CNY"
    crawl_enabled: bool = False


# ================= 人生手札 =================
# ---------- 媒体 ----------
class MediaAttachIn(BaseModel):
    """把「未归类照片」挂到某条主记录（先存照片、稍后归类）。"""
    asset_ids: list[int] = Field(default_factory=list, max_length=60)
    owner_type: Literal["ledger", "trip", "event", "countdown"]
    owner_id: int


# ---------- 账本 ----------
class LedgerCreate(BaseModel):
    direction: Literal["expense", "income"] = "expense"
    amount: float = Field(gt=0, le=9999999.99)
    category: str = Field(min_length=1, max_length=20)
    account: Optional[str] = Field(default=None, max_length=20)
    occurred_on: Date
    note: Optional[str] = Field(default=None, max_length=50)
    media_id: Optional[int] = None


class LedgerUpdate(BaseModel):
    direction: Optional[Literal["expense", "income"]] = None
    amount: Optional[float] = Field(default=None, gt=0, le=9999999.99)
    category: Optional[str] = Field(default=None, min_length=1, max_length=20)
    account: Optional[str] = Field(default=None, max_length=20)
    occurred_on: Optional[Date] = None
    note: Optional[str] = Field(default=None, max_length=50)
    media_id: Optional[int] = None


class LedgerCategoryIn(BaseModel):
    name: str = Field(min_length=1, max_length=10)
    emoji: str = Field(default="📦", max_length=8)


# ---------- 日子 ----------
class CountdownCreate(BaseModel):
    name: str = Field(min_length=1, max_length=20)
    date: Date
    repeat_rule: Literal["once", "yearly", "monthly", "yearly_lunar", "anniversary"] = "once"
    remind_offsets: list[int] = Field(default_factory=lambda: [7, 0])
    emoji: str = Field(default="🎯", max_length=8)
    color: Optional[str] = Field(default=None, max_length=20)
    note: Optional[str] = Field(default=None, max_length=100)


class CountdownUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=20)
    date: Optional[Date] = None
    repeat_rule: Optional[Literal["once", "yearly", "monthly", "yearly_lunar", "anniversary"]] = None
    remind_offsets: Optional[list[int]] = None
    emoji: Optional[str] = Field(default=None, max_length=8)
    color: Optional[str] = Field(default=None, max_length=20)
    note: Optional[str] = Field(default=None, max_length=100)
    pinned: Optional[bool] = None


# ---------- 足迹 · 旅游 ----------
class TripCreate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=30)
    destinations: list[str] = Field(min_length=1, max_length=5)
    start_date: Date
    end_date: Date
    companions: Optional[str] = Field(default=None, max_length=30)
    content: Optional[str] = Field(default=None, max_length=1000)
    cost: Optional[float] = Field(default=None, ge=0)
    cover_media_id: Optional[int] = None
    media_ids: list[int] = Field(default_factory=list, max_length=60)


class TripUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=30)
    destinations: Optional[list[str]] = Field(default=None, max_length=5)
    start_date: Optional[Date] = None
    end_date: Optional[Date] = None
    companions: Optional[str] = Field(default=None, max_length=30)
    content: Optional[str] = Field(default=None, max_length=1000)
    cost: Optional[float] = Field(default=None, ge=0)
    cover_media_id: Optional[int] = None
    media_ids: Optional[list[int]] = None


# ---------- 足迹 · 大事件 ----------
class EventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=30)
    event_date: Date
    category: str = Field(default="里程碑", max_length=20)
    emoji: str = Field(default="🎉", max_length=8)
    mood: Optional[str] = Field(default=None, max_length=8)
    content: Optional[str] = Field(default=None, max_length=2000)
    tags: list[str] = Field(default_factory=list, max_length=5)
    media_ids: list[int] = Field(default_factory=list, max_length=30)


class EventUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=30)
    event_date: Optional[Date] = None
    category: Optional[str] = Field(default=None, max_length=20)
    emoji: Optional[str] = Field(default=None, max_length=8)
    mood: Optional[str] = Field(default=None, max_length=8)
    content: Optional[str] = Field(default=None, max_length=2000)
    tags: Optional[list[str]] = Field(default=None, max_length=5)
    media_ids: Optional[list[int]] = None


# ---------- 家庭资产 ----------
class AssetItemCreate(BaseModel):
    category: Literal["cash", "property", "vehicle", "other", "liability"]
    sub_category: Optional[str] = Field(default=None, max_length=20)
    name: str = Field(min_length=1, max_length=30)
    amount: float = Field(ge=0)
    currency: Literal["CNY", "USD", "HKD"] = "CNY"
    note: Optional[str] = Field(default=None, max_length=100)
    repay_date: Optional[Date] = None


class AssetItemUpdate(BaseModel):
    sub_category: Optional[str] = Field(default=None, max_length=20)
    name: Optional[str] = Field(default=None, min_length=1, max_length=30)
    amount: Optional[float] = Field(default=None, ge=0)
    currency: Optional[Literal["CNY", "USD", "HKD"]] = None
    note: Optional[str] = Field(default=None, max_length=100)
    repay_date: Optional[Date] = None


# ---------- 待办（值得记 · 待办）----------
class TodoCreate(BaseModel):
    title: str = Field(min_length=1, max_length=60)
    due_date: Optional[Date] = None
    note: Optional[str] = Field(default=None, max_length=200)
    important: bool = False


class TodoUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=60)
    due_date: Optional[Date] = None
    note: Optional[str] = Field(default=None, max_length=200)
    important: Optional[bool] = None
    done: Optional[bool] = None


# ---------- 树洞（发现 · 公共频道）----------
class TreeholeCreate(BaseModel):
    content: str = Field(min_length=2, max_length=200)


class TreeholeReportIn(BaseModel):
    reason: Optional[str] = Field(default=None, max_length=100)


class TreeholeRejectIn(BaseModel):
    reason: str = Field(min_length=1, max_length=100)
