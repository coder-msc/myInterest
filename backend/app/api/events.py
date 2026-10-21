"""足迹 · 人生大事件接口（PRD M4）：按年份分组的时间线。"""
import json
from datetime import date

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..database import get_session
from ..models import LifeEvent, User
from ..schemas import EventCreate, EventUpdate
from ..services import config_service, entry_service, media_service, recycle_service
from ..utils.errors import not_found, ok
from ..utils.timeutil import now_str
from .deps import get_current_user, require_module

router = APIRouter(prefix="/api/events", tags=["events"],
                   dependencies=[Depends(require_module("module_events_enabled"))])

PRESET_CATEGORIES = [
    {"name": "工作", "emoji": "💼"}, {"name": "学业", "emoji": "🎓"},
    {"name": "家庭", "emoji": "🏡"}, {"name": "健康", "emoji": "🌱"},
    {"name": "财务", "emoji": "💰"}, {"name": "里程碑", "emoji": "🏆"},
]


def _owned(session: Session, user_id: int, event_id: int) -> LifeEvent:
    e = session.get(LifeEvent, event_id)
    if e is None or e.user_id != user_id or e.status != "normal":
        raise not_found("这条大事件不存在或已删除")
    return e


def event_out(session: Session, e: LifeEvent, with_media: bool = True) -> dict:
    media = media_service.list_for_owner(session, e.user_id, "event", e.id)
    return {
        "id": e.id, "title": e.title, "event_date": e.event_date,
        "category": e.category, "emoji": e.emoji, "mood": e.mood,
        "content": e.content, "tags": json.loads(e.tags or "[]"),
        "is_future": e.event_date > date.today().isoformat(),
        "cover_url": media_service.asset_url(media[0]) if media else None,
        "photo_count": len(media),
        "photos": [media_service.asset_out(a) for a in media] if with_media else [],
        "created_at": e.created_at,
    }


@router.get("")
def listing(session: Session = Depends(get_session),
            user: User = Depends(get_current_user)):
    rows = session.exec(select(LifeEvent)
                        .where(LifeEvent.user_id == user.id)
                        .where(LifeEvent.status == "normal")).all()
    items = [event_out(session, e, with_media=False) for e in rows]
    items.sort(key=lambda x: x["event_date"], reverse=True)
    groups: dict[str, list[dict]] = {}
    for it in items:
        groups.setdefault(it["event_date"][:4], []).append(it)
    return ok({"groups": [{"year": y, "count": len(v), "items": v}
                          for y, v in sorted(groups.items(), reverse=True)],
               "total": len(items), "categories": PRESET_CATEGORIES,
               "photo_limit": config_service.get_int("media_max_per_event")})


@router.get("/{event_id}")
def detail(event_id: int, session: Session = Depends(get_session),
           user: User = Depends(get_current_user)):
    return ok(event_out(session, _owned(session, user.id, event_id)))


@router.post("")
def create(body: EventCreate, session: Session = Depends(get_session),
           user: User = Depends(get_current_user)):
    limit = config_service.get_int("media_max_per_event")
    e = LifeEvent(user_id=user.id, title=body.title,
                  event_date=body.event_date.isoformat(), category=body.category,
                  emoji=body.emoji, mood=body.mood, content=body.content,
                  tags=json.dumps(body.tags[:5], ensure_ascii=False) if body.tags else None)
    session.add(e)
    session.flush()
    media_service.attach(session, user.id, body.media_ids[:limit], "event", e.id)
    session.flush()
    entry_service._from_event(session, e)
    session.commit()
    session.refresh(e)
    return ok(event_out(session, e))


@router.patch("/{event_id}")
def update(event_id: int, body: EventUpdate, session: Session = Depends(get_session),
           user: User = Depends(get_current_user)):
    e = _owned(session, user.id, event_id)
    data = body.model_dump(exclude_unset=True)
    if "event_date" in data and data["event_date"]:
        e.event_date = data.pop("event_date").isoformat()
    if "tags" in data and data["tags"] is not None:
        e.tags = json.dumps(data.pop("tags")[:5], ensure_ascii=False)
    if "media_ids" in data:
        ids = (data.pop("media_ids") or [])[:config_service.get_int("media_max_per_event")]
        media_service.attach(session, user.id, ids, "event", e.id)
        media_service.replace_owner_media(session, user.id, "event", e.id, ids)
    for k, v in data.items():
        if v is not None:
            setattr(e, k, v)
    e.updated_at = now_str()
    session.add(e)
    session.flush()
    entry_service._from_event(session, e)
    session.commit()
    session.refresh(e)
    return ok(event_out(session, e))


@router.delete("/{event_id}")
def remove(event_id: int, session: Session = Depends(get_session),
           user: User = Depends(get_current_user)):
    _owned(session, user.id, event_id)
    info = recycle_service.soft_delete(session, user.id, "event", event_id)
    session.commit()
    return ok(info)
