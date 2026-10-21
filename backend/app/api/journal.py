"""手札流（PRD M1）：首页聚合 + 时间线 + 全局搜索。

时间线【只查条目索引层】，不直接查各模块主表；索引层与主表不一致时，
点进条目发现主记录不存在，前端展示「这条记录已不存在」并静默移除。
"""
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from ..database import get_session
from ..models import Countdown, ReminderMessage, User
from ..services import asset_service, countdown_service, entry_service, ledger_service
from ..utils.errors import ok
from .deps import get_current_user

router = APIRouter(prefix="/api/journal", tags=["journal"])


def _headline(counts: dict) -> str:
    total = sum(counts.values())
    if total == 0:
        return "你的手札还是一片空白"
    if total < 5:
        return f"已经记下 {total} 条，起步了"
    return f"已经记下 {total} 条人生碎片"


@router.get("/home")
def home(page: int = Query(default=1, ge=1),
         page_size: int = Query(default=20, ge=1, le=50),
         entry_type: str | None = None,
         session: Session = Depends(get_session),
         user: User = Depends(get_current_user)):
    """首页一次性拉齐：月度小结 + 置顶日子条 + 时间线 + 资产快捷卡。"""
    from ..utils.timeutil import today_str
    month = today_str()[:7]
    led = ledger_service.summary(session, user.id, month)
    counts = entry_service.counts_by_type(session, user.id)

    # 置顶日子条：优先置顶中最近的一条，没有置顶取最近的
    cds = session.exec(select(Countdown)
                       .where(Countdown.user_id == user.id)
                       .where(Countdown.status == "normal")).all()
    items = [countdown_service.out(c) for c in cds]
    active = [i for i in items if not i["is_past"]]
    pinned = [i for i in active if i["pinned"]]
    top_day = min(pinned or active, key=lambda i: i["days_left"]) if (pinned or active) else None

    feed = entry_service.feed(session, user.id, page, page_size, entry_type)

    unread = len(session.exec(select(ReminderMessage)
                              .where(ReminderMessage.user_id == user.id)
                              .where(ReminderMessage.read_at.is_(None))).all())

    # 本月新增足迹/大事件（月度小结卡的追加一行）
    this_month_types = [e for e in feed["items"]
                        if e["occurred_at"][:7] == month and e["entry_type"] in ("trip", "event")]

    return ok({
        "month_summary": led,
        "has_prev_month": led["has_prev"],
        "headline": _headline(counts),
        "counts": counts,
        "top_day": top_day,
        "feed": feed,
        "unread": unread,
        "month_footprints": len(this_month_types),
        "asset_card": _asset_card(session, user.id),
    })


def _asset_card(session: Session, user_id: int):
    """家庭资产快捷卡：仅在已有资产数据时出现（低频入口的兜底存在感，PRD §M1）。"""
    from ..services import config_service
    if not config_service.get_bool("module_assets_enabled"):
        return None
    ov = asset_service.overview(session, user_id)
    if not ov["has_data"]:
        return None
    return {"net_worth": ov["net_worth"], "last_snapshot": ov["last_snapshot"]}


@router.get("/feed")
def feed(page: int = Query(default=1, ge=1),
         page_size: int = Query(default=20, ge=1, le=50),
         entry_type: str | None = None,
         session: Session = Depends(get_session),
         user: User = Depends(get_current_user)):
    return ok(entry_service.feed(session, user.id, page, page_size, entry_type))


@router.get("/search")
def search(q: str = Query(min_length=1, max_length=40),
           session: Session = Depends(get_session),
           user: User = Depends(get_current_user)):
    return ok(entry_service.search(session, user.id, q))


@router.get("/counts")
def counts(session: Session = Depends(get_session),
           user: User = Depends(get_current_user)):
    """「我的」页与后台看板用的各模块条目统计。"""
    return ok(entry_service.counts_by_type(session, user.id))


@router.get("/stats")
def stats(session: Session = Depends(get_session),
          user: User = Depends(get_current_user)):
    """注销前展示「将删除多少条记录、多少张照片」（PRD M7 二次确认要求）。"""
    from ..models import MediaAsset
    c = entry_service.counts_by_type(session, user.id)
    photos = len(session.exec(select(MediaAsset)
                              .where(MediaAsset.user_id == user.id)
                              .where(MediaAsset.status == "normal")).all())
    return ok({"counts": c, "total": sum(c.values()), "photos": photos})


@router.post("/rebuild-index")
def rebuild(session: Session = Depends(get_session),
            user: User = Depends(get_current_user)):
    """索引层可重建（PRD §4.2）：写坏时的兜底修复入口。"""
    n = entry_service.rebuild_all(session, user.id)
    return ok({"rebuilt": n})


@router.get("/modules")
def modules(user: User = Depends(get_current_user)):
    """前端 tab / 入口的灰度开关状态（PRD §7.5）。"""
    from ..services import config_service
    return ok({
        "ledger": config_service.get_bool("module_ledger_enabled"),
        "days": config_service.get_bool("module_days_enabled"),
        "trips": config_service.get_bool("module_trips_enabled"),
        "events": config_service.get_bool("module_events_enabled"),
        "assets": config_service.get_bool("module_assets_enabled"),
    })
