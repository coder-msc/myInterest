"""条目索引层服务（PRD §4.2）。

硬约束：本模块的所有写操作【不 commit】—— 由调用方（模块 API）把主表写入与
索引写入放进同一个事务后统一提交。这样才不会出现「手札流有条目、点进去 404」。

索引层可全量重建（rebuild_all）：任何时候都由各模块主表重新生成，写坏也能修。
"""
import json
from typing import Optional

from sqlmodel import Session, select

from ..models import (AssetSnapshot, Countdown, EntryIndex, LedgerRecord, LifeEvent,
                      MediaAsset, Trip)
from ..utils.timeutil import now_str

# 条目类型 → 中文标签（前端徽章文案的唯一来源）
TYPE_LABEL = {
    "ledger": "账本",
    "trip": "旅游",
    "event": "大事件",
    "countdown": "日子",
    "asset_snapshot": "资产盘点",
}


def _dump(v) -> Optional[str]:
    return None if v is None else json.dumps(v, ensure_ascii=False)


def _load(raw: Optional[str]):
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


def upsert(session: Session, user_id: int, entry_type: str, ref_id: int,
           occurred_at: str, title: str, summary: Optional[str] = None,
           cover_media_id: Optional[int] = None,
           tags: Optional[list] = None, extra: Optional[dict] = None) -> EntryIndex:
    """创建或更新一条索引（同 user+type+ref 幂等）。不 commit。"""
    row = session.exec(select(EntryIndex)
                       .where(EntryIndex.user_id == user_id)
                       .where(EntryIndex.entry_type == entry_type)
                       .where(EntryIndex.ref_id == ref_id)).first()
    if row is None:
        row = EntryIndex(user_id=user_id, entry_type=entry_type, ref_id=ref_id,
                         occurred_at=occurred_at, occurred_ts=now_str(),
                         title=title, summary=summary, cover_media_id=cover_media_id,
                         tags=_dump(tags), extra=_dump(extra))
    else:
        row.occurred_at = occurred_at  # 补记历史记录时回到原位（排序按发生时间）
        row.title, row.summary = title, summary
        row.cover_media_id = cover_media_id
        row.tags, row.extra = _dump(tags), _dump(extra)
        row.updated_at = now_str()
    session.add(row)
    return row


def set_status(session: Session, user_id: int, entry_type: str, ref_id: int,
               status: str, deleted_at: Optional[str] = None) -> None:
    """跟随主表软删除状态同步隐藏/恢复（PRD §7.1）。不 commit。"""
    row = session.exec(select(EntryIndex)
                       .where(EntryIndex.user_id == user_id)
                       .where(EntryIndex.entry_type == entry_type)
                       .where(EntryIndex.ref_id == ref_id)).first()
    if row is None:
        return
    row.status = status
    row.deleted_at = deleted_at if status == "deleted" else None
    row.updated_at = now_str()
    session.add(row)


def drop(session: Session, user_id: int, entry_type: str, ref_id: int) -> None:
    """主记录彻底销毁时删除索引行（索引层不承担回收站逻辑）。不 commit。"""
    row = session.exec(select(EntryIndex)
                       .where(EntryIndex.user_id == user_id)
                       .where(EntryIndex.entry_type == entry_type)
                       .where(EntryIndex.ref_id == ref_id)).first()
    if row is not None:
        session.delete(row)


def feed(session: Session, user_id: int, page: int = 1, page_size: int = 20,
         entry_type: Optional[str] = None) -> dict:
    """手札流：只查索引层，按发生时间倒序分页（PRD §M1）。"""
    stmt = select(EntryIndex).where(EntryIndex.user_id == user_id) \
                             .where(EntryIndex.status == "normal")
    if entry_type:
        stmt = stmt.where(EntryIndex.entry_type == entry_type)
    rows = session.exec(stmt.order_by(EntryIndex.occurred_at.desc(),
                                      EntryIndex.occurred_ts.desc(),
                                      EntryIndex.id.desc())
                        .offset((page - 1) * page_size).limit(page_size)).all()
    total = len(session.exec(stmt).all())
    return {"items": [out(r, session) for r in rows],
            "page": page, "page_size": page_size, "total": total,
            "has_more": page * page_size < total}


def search(session: Session, user_id: int, keyword: str, limit: int = 50) -> list[dict]:
    """全局搜索：标题 + 摘要 + 标签，走索引层（PRD §4.2）。"""
    kw = (keyword or "").strip()
    if not kw:
        return []
    like = f"%{kw}%"
    rows = session.exec(select(EntryIndex)
                        .where(EntryIndex.user_id == user_id)
                        .where(EntryIndex.status == "normal")
                        .where(EntryIndex.title.like(like)
                               | EntryIndex.summary.like(like)
                               | EntryIndex.tags.like(like))
                        .order_by(EntryIndex.occurred_at.desc())
                        .limit(limit)).all()
    return [out(r, session) for r in rows]


def _cover_url(session: Session, media_id: Optional[int], user_id: int) -> Optional[str]:
    if not media_id:
        return None
    a = session.get(MediaAsset, media_id)
    if a is None or a.user_id != user_id or a.status != "normal":
        return None
    from . import media_service
    return media_service.asset_url(a)


def out(row: EntryIndex, session: Optional[Session] = None) -> dict:
    cover = None
    if row.cover_media_id and session is not None:
        cover = _cover_url(session, row.cover_media_id, row.user_id)
    return {
        "id": row.id, "entry_type": row.entry_type, "type_label": TYPE_LABEL.get(row.entry_type, ""),
        "ref_id": row.ref_id, "occurred_at": row.occurred_at, "title": row.title,
        "summary": row.summary, "tags": _load(row.tags) or [],
        "extra": _load(row.extra) or {}, "cover_url": cover,
    }


def counts_by_type(session: Session, user_id: Optional[int] = None) -> dict:
    """各模块条目总数（后台看板 / 用户「我的」页统计）。"""
    stmt = select(EntryIndex).where(EntryIndex.status == "normal")
    if user_id is not None:
        stmt = stmt.where(EntryIndex.user_id == user_id)
    result = {k: 0 for k in TYPE_LABEL}
    for r in session.exec(stmt).all():
        result[r.entry_type] = result.get(r.entry_type, 0) + 1
    return result


# ── 全量重建（索引可重建：写坏也能修） ─────────────────────────
def rebuild_all(session: Session, user_id: Optional[int] = None) -> int:
    stmt = select(EntryIndex)
    if user_id is not None:
        stmt = stmt.where(EntryIndex.user_id == user_id)
    for r in session.exec(stmt).all():
        session.delete(r)
    session.flush()
    n = 0
    for model, builder in ((LedgerRecord, _from_ledger), (Trip, _from_trip),
                           (LifeEvent, _from_event), (Countdown, _from_countdown),
                           (AssetSnapshot, _from_snapshot)):
        stmt2 = select(model)
        if user_id is not None:
            stmt2 = stmt2.where(model.user_id == user_id)
        for rec in session.exec(stmt2).all():
            if rec.status == "deleted":
                continue
            builder(session, rec)
            n += 1
    session.commit()
    return n


def _from_ledger(session: Session, r: LedgerRecord) -> None:
    sign = "-" if r.direction == "expense" else "+"
    upsert(session, r.user_id, "ledger", r.id, r.occurred_on, r.note or r.category,
           summary=f"{r.category} · {r.account or '未选账户'}",
           cover_media_id=r.media_id,
           extra={"amount": round(r.amount, 2), "direction": r.direction,
                  "amount_text": f"{sign}{r.amount:,.2f}"})


def _from_trip(session: Session, r: Trip) -> None:
    dests = json.loads(r.destinations or "[]")
    media = session.exec(select(MediaAsset)
                         .where(MediaAsset.owner_type == "trip")
                         .where(MediaAsset.owner_id == r.id)
                         .where(MediaAsset.status == "normal")
                         .order_by(MediaAsset.sort_order)).all()
    upsert(session, r.user_id, "trip", r.id, r.start_date, r.title,
           summary=f"{' · '.join(dests)} · {r.start_date} 至 {r.end_date}",
           cover_media_id=r.cover_media_id or (media[0].id if media else None),
           extra={"destinations": dests, "start_date": r.start_date,
                  "end_date": r.end_date, "photo_count": len(media)})


def _from_event(session: Session, r: LifeEvent) -> None:
    media = session.exec(select(MediaAsset)
                         .where(MediaAsset.owner_type == "event")
                         .where(MediaAsset.owner_id == r.id)
                         .where(MediaAsset.status == "normal")).all()
    upsert(session, r.user_id, "event", r.id, r.event_date, r.title,
           summary=f"{r.emoji} {r.category}",
           cover_media_id=media[0].id if media else None,
           tags=json.loads(r.tags or "[]") or None,
           extra={"emoji": r.emoji, "mood": r.mood, "category": r.category,
                  "photo_count": len(media)})


def _from_countdown(session: Session, r: Countdown) -> None:
    from . import countdown_service
    nxt = countdown_service.next_occurrence(r)
    upsert(session, r.user_id, "countdown", r.id, nxt["solar_date"], r.name,
           summary=nxt["label"],
           extra={"emoji": r.emoji, "repeat_rule": r.repeat_rule,
                  "lunar_text": r.lunar_text, "year_no": nxt.get("year_no")})


def _from_snapshot(session: Session, r: AssetSnapshot) -> None:
    upsert(session, r.user_id, "asset_snapshot", r.id, r.snapshot_date,
           "资产盘点", summary=f"净值 ¥{r.net_worth:,.2f}",
           extra={"net_worth": r.net_worth})
