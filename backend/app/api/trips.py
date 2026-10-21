"""足迹 · 旅游接口（PRD M3）：行程 CRUD + 照片集 + 城市统计。"""
import json
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from ..database import get_session
from ..models import Trip, User
from ..schemas import TripCreate, TripUpdate
from ..services import config_service, entry_service, media_service, recycle_service
from ..utils.errors import AppError, Codes, not_found, ok
from ..utils.timeutil import now_str
from .deps import get_current_user, require_module

router = APIRouter(prefix="/api/trips", tags=["trips"],
                   dependencies=[Depends(require_module("module_trips_enabled"))])


def _owned(session: Session, user_id: int, trip_id: int) -> Trip:
    t = session.get(Trip, trip_id)
    if t is None or t.user_id != user_id or t.status != "normal":
        raise not_found("这趟行程不存在或已删除")
    return t


def _photo_limit() -> int:
    return config_service.get_int("media_max_per_trip")


def _default_title(dests: list[str], start: date, end: date) -> str:
    span = f"{start.month}月{start.day}日" if start == end else \
        f"{start.month}月{start.day}日-{end.month}月{end.day}日"
    return f"{'、'.join(dests[:2])} · {span}"[:30]


def _status_of(t: Trip, today: date) -> str:
    try:
        end = date.fromisoformat(t.end_date)
        start = date.fromisoformat(t.start_date)
    except Exception:
        return "ended"
    if today < start:
        return "upcoming"
    return "ongoing" if today <= end else "ended"


def trip_out(session: Session, t: Trip, with_media: bool = True) -> dict:
    media = media_service.list_for_owner(session, t.user_id, "trip", t.id)
    cover = None
    if t.cover_media_id:
        cover = next((media_service.asset_url(a) for a in media if a.id == t.cover_media_id), None)
    if not cover and media:
        cover = media_service.asset_url(media[0])
    return {
        "id": t.id, "title": t.title, "destinations": json.loads(t.destinations or "[]"),
        "start_date": t.start_date, "end_date": t.end_date, "companions": t.companions,
        "cost": t.cost, "content": t.content,
        "status": _status_of(t, date.today()),
        "cover_url": cover, "photo_count": len(media),
        "photos": [media_service.asset_out(a) for a in media] if with_media else [],
        "created_at": t.created_at,
    }


@router.get("")
def listing(session: Session = Depends(get_session),
            user: User = Depends(get_current_user)):
    rows = session.exec(select(Trip)
                        .where(Trip.user_id == user.id)
                        .where(Trip.status == "normal")).all()
    items = [trip_out(session, t, with_media=False) for t in rows]
    # 进行中的排最前，其余按开始日期倒序
    items.sort(key=lambda x: (0 if x["status"] == "ongoing" else 1,))
    items.sort(key=lambda x: x["start_date"], reverse=True)
    items.sort(key=lambda x: 0 if x["status"] == "ongoing" else 1)

    cities = {c for it in items for c in it["destinations"]}
    return ok({"items": items, "city_count": len(cities), "trip_count": len(items),
               "photo_limit": _photo_limit()})


@router.get("/{trip_id}")
def detail(trip_id: int, session: Session = Depends(get_session),
           user: User = Depends(get_current_user)):
    return ok(trip_out(session, _owned(session, user.id, trip_id)))


@router.post("")
def create(body: TripCreate, session: Session = Depends(get_session),
           user: User = Depends(get_current_user)):
    if body.end_date < body.start_date:
        raise AppError(Codes.VALIDATION, "结束日期不能早于开始日期", status=422)
    dests = [d.strip() for d in body.destinations if d.strip()][:5]
    if not dests:
        raise AppError(Codes.VALIDATION, "目的地（城市）为必填", status=422)
    media_ids = body.media_ids[:_photo_limit()]
    t = Trip(user_id=user.id,
             title=(body.title or _default_title(dests, body.start_date, body.end_date)),
             destinations=json.dumps(dests, ensure_ascii=False),
             start_date=body.start_date.isoformat(), end_date=body.end_date.isoformat(),
             companions=body.companions, content=body.content, cost=body.cost)
    session.add(t)
    session.flush()
    media_service.attach(session, user.id, media_ids, "trip", t.id)
    media_service.replace_owner_media(session, user.id, "trip", t.id, media_ids)
    if body.cover_media_id:
        t.cover_media_id = body.cover_media_id
    session.add(t)
    session.flush()
    entry_service._from_trip(session, t)
    session.commit()
    session.refresh(t)
    return ok(trip_out(session, t))


@router.patch("/{trip_id}")
def update(trip_id: int, body: TripUpdate, session: Session = Depends(get_session),
           user: User = Depends(get_current_user)):
    t = _owned(session, user.id, trip_id)
    data = body.model_dump(exclude_unset=True)
    if "destinations" in data and data["destinations"] is not None:
        dests = [d.strip() for d in data.pop("destinations") if d.strip()][:5]
        if not dests:
            raise AppError(Codes.VALIDATION, "目的地（城市）为必填", status=422)
        t.destinations = json.dumps(dests, ensure_ascii=False)
    for key in ("start_date", "end_date"):
        if key in data and data[key] is not None:
            data[key] = data[key].isoformat()
    if "media_ids" in data:
        ids = (data.pop("media_ids") or [])[:_photo_limit()]
        media_service.attach(session, user.id, ids, "trip", t.id)
        media_service.replace_owner_media(session, user.id, "trip", t.id, ids)
        if t.cover_media_id and t.cover_media_id not in ids:
            t.cover_media_id = None
    for k, v in data.items():
        if v is not None:
            setattr(t, k, v)
    if date.fromisoformat(t.end_date) < date.fromisoformat(t.start_date):
        raise AppError(Codes.VALIDATION, "结束日期不能早于开始日期", status=422)
    t.updated_at = now_str()
    session.add(t)
    session.flush()
    entry_service._from_trip(session, t)
    session.commit()
    session.refresh(t)
    return ok(trip_out(session, t))


@router.delete("/{trip_id}")
def remove(trip_id: int, session: Session = Depends(get_session),
           user: User = Depends(get_current_user)):
    _owned(session, user.id, trip_id)
    info = recycle_service.soft_delete(session, user.id, "trip", trip_id)
    session.commit()
    return ok(info)
