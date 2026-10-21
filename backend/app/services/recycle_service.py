"""统一软删除与回收站（PRD §7.1）。

三态：正常 → 已删除（回收站，保留 N 天）→ 已销毁（到期清理，含照片文件）。
不做「彻底删除」的用户选项 —— 用户要的是后悔药。
"""
import json
from datetime import datetime, timedelta
from typing import Optional

from sqlmodel import Session, select

from ..models import AssetItem, Countdown, LedgerRecord, LifeEvent, Trip
from ..utils.timeutil import now_str
from . import entry_service, media_service

# 条目类型 → 主表模型（回收站按模块分组的数据来源）
MODEL_MAP = {
    "ledger": LedgerRecord,
    "trip": Trip,
    "event": LifeEvent,
    "countdown": Countdown,
    "asset_item": AssetItem,
}

GROUP_LABEL = {"ledger": "账本", "trip": "旅游", "event": "大事件",
               "countdown": "日子", "asset_item": "家庭资产"}

# 各类型的标题与发生时间字段（回收站列表展示用）
_TITLE_FIELD = {"ledger": "note", "trip": "title", "event": "title",
                "countdown": "name", "asset_item": "name"}
_DATE_FIELD = {"ledger": "occurred_on", "trip": "start_date", "event": "event_date",
               "countdown": "base_date", "asset_item": "updated_at"}


def retain_days() -> int:
    from . import config_service
    return config_service.get_int("recycle_retain_days")


def soft_delete(session: Session, user_id: int, entry_type: str, ref_id: int) -> dict:
    """软删除一条主记录：标记状态 + 同步索引 + 照片进回收站。不 commit。"""
    model = MODEL_MAP.get(entry_type)
    if model is None:
        return {}
    rec = session.get(model, ref_id)
    if rec is None or rec.user_id != user_id:
        return {}
    ts = now_str()
    rec.status, rec.deleted_at = "deleted", ts
    session.add(rec)
    if entry_type != "asset_item":
        entry_service.set_status(session, user_id, entry_type, ref_id, "deleted", ts)
    media_service.soft_delete_owner(session, user_id, entry_type, ref_id)
    return {"type": entry_type, "id": ref_id, "days_left": retain_days()}


def restore(session: Session, user_id: int, entry_type: str, ref_id: int) -> bool:
    model = MODEL_MAP.get(entry_type)
    if model is None:
        return False
    rec = session.get(model, ref_id)
    if rec is None or rec.user_id != user_id or rec.status != "deleted":
        return False
    rec.status, rec.deleted_at = "normal", None
    session.add(rec)
    if entry_type != "asset_item":
        entry_service.set_status(session, user_id, entry_type, ref_id, "normal")
    media_service.restore_owner(session, user_id, entry_type, ref_id)
    return True


def _days_left(deleted_at: Optional[str]) -> int:
    if not deleted_at:
        return 0
    try:
        dt = datetime.strptime(deleted_at, "%Y-%m-%d %H:%M:%S")
    except Exception:
        return 0
    return max(retain_days() - (datetime.now() - dt).days, 0)


def listing(session: Session, user_id: int) -> dict:
    """回收站：按模块分组，带「剩余可恢复天数」。"""
    groups = []
    for entry_type, model in MODEL_MAP.items():
        rows = session.exec(select(model)
                            .where(model.user_id == user_id)
                            .where(model.status == "deleted")).all()
        if not rows:
            continue
        items = []
        for r in rows:
            title = getattr(r, _TITLE_FIELD[entry_type], None) or "未命名"
            date_field = _DATE_FIELD[entry_type]
            occurred = getattr(r, date_field, None)
            items.append({"id": r.id, "type": entry_type, "title": title,
                          "occurred_at": str(occurred)[:10] if occurred else "",
                          "deleted_at": r.deleted_at,
                          "days_left": _days_left(r.deleted_at)})
        groups.append({"type": entry_type, "label": GROUP_LABEL[entry_type],
                       "count": len(items), "items": items})
    return {"groups": groups, "retain_days": retain_days(),
            "total": sum(g["count"] for g in groups)}


def purge_expired(session: Session) -> int:
    """销毁超过保留期的条目：照片真删 + 主记录删除 + 索引删除。"""
    from . import entry_service, media_service
    from ..models import MediaAsset
    days = retain_days()
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    purged = 0
    for entry_type, model in MODEL_MAP.items():
        rows = session.exec(select(model)
                            .where(model.status == "deleted")
                            .where(model.deleted_at < cutoff)).all()
        for r in rows:
            # 照片：先真删文件，再标记 purged
            for a in session.exec(select(MediaAsset)
                                  .where(MediaAsset.owner_type == entry_type)
                                  .where(MediaAsset.owner_id == r.id)).all():
                media_service.purge_asset(session, a)
            if entry_type != "asset_item":
                entry_service.drop(session, r.user_id, entry_type, r.id)
            session.delete(r)
            purged += 1
    if purged:
        session.commit()
    return purged
