"""日子接口（PRD M5）：倒计时 CRUD + 重复规则推进 + 提醒档位。"""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from ..database import get_session
from ..models import Countdown, User
from ..schemas import CountdownCreate, CountdownUpdate
from ..services import countdown_service, entry_service, recycle_service
from ..utils.errors import AppError, Codes, not_found, ok
from ..utils.timeutil import now_str
from .deps import get_current_user, require_module

router = APIRouter(prefix="/api/countdowns", tags=["countdowns"],
                   dependencies=[Depends(require_module("module_days_enabled"))])

MAX_PINNED = 3


def _owned(session: Session, user_id: int, cd_id: int) -> Countdown:
    cd = session.get(Countdown, cd_id)
    if cd is None or cd.user_id != user_id or cd.status != "normal":
        raise not_found("这个日子不存在或已删除")
    return cd


@router.get("")
def listing(month: str | None = Query(default=None, max_length=7),
            session: Session = Depends(get_session),
            user: User = Depends(get_current_user)):
    rows = session.exec(select(Countdown)
                        .where(Countdown.user_id == user.id)
                        .where(Countdown.status == "normal")).all()
    items = [countdown_service.out(c) for c in rows]
    items.sort(key=countdown_service.sort_key)
    if month:
        # 月历视图：按「下一次发生日期」落在该月的日子过滤
        items = [i for i in items if i["next_date"][:7] == month]
    return ok({"items": items,
               "pinned_count": len([i for i in items if i["pinned"]]),
               "max_pinned": MAX_PINNED})


@router.get("/{cd_id}")
def detail(cd_id: int, session: Session = Depends(get_session),
           user: User = Depends(get_current_user)):
    return ok(countdown_service.out(_owned(session, user.id, cd_id)))


def _lunar_fields(rule: str, d: date) -> dict:
    if rule != "yearly_lunar":
        return {"lunar_month": None, "lunar_day": None, "lunar_text": None}
    m, day, text = countdown_service.solar_to_lunar(d)
    return {"lunar_month": m, "lunar_day": day, "lunar_text": text}


@router.post("")
def create(body: CountdownCreate, session: Session = Depends(get_session),
           user: User = Depends(get_current_user)):
    cd = Countdown(user_id=user.id, name=body.name, base_date=body.date.isoformat(),
                   repeat_rule=body.repeat_rule,
                   remind_offsets=str(sorted(set(body.remind_offsets or [7, 0]), reverse=True)).replace(" ", ""),
                   emoji=body.emoji, color=body.color, note=body.note,
                   **_lunar_fields(body.repeat_rule, body.date))
    session.add(cd)
    session.flush()
    entry_service._from_countdown(session, cd)
    session.commit()
    session.refresh(cd)
    return ok(countdown_service.out(cd))


@router.patch("/{cd_id}")
def update(cd_id: int, body: CountdownUpdate, session: Session = Depends(get_session),
           user: User = Depends(get_current_user)):
    cd = _owned(session, user.id, cd_id)
    data = body.model_dump(exclude_unset=True)

    if "pinned" in data:
        pinned = bool(data.pop("pinned"))
        if pinned and not cd.pinned:
            n = len(session.exec(select(Countdown)
                                 .where(Countdown.user_id == user.id)
                                 .where(Countdown.status == "normal")
                                 .where(Countdown.pinned == 1)).all())
            if n >= MAX_PINNED:
                raise AppError(Codes.VALIDATION,
                               f"最多置顶 {MAX_PINNED} 个，先取消一个吧", status=422)
        cd.pinned = 1 if pinned else 0

    if "date" in data and data["date"]:
        cd.base_date = data.pop("date").isoformat()
    if "repeat_rule" in data and data["repeat_rule"]:
        cd.repeat_rule = data.pop("repeat_rule")
    if "remind_offsets" in data and data["remind_offsets"] is not None:
        vals = sorted({int(v) for v in data.pop("remind_offsets")
                       if int(v) in countdown_service.REMIND_CHOICES}, reverse=True)
        cd.remind_offsets = str(vals).replace(" ", "")
    for k, v in data.items():
        if v is not None:
            setattr(cd, k, v)

    lunar = _lunar_fields(cd.repeat_rule, date.fromisoformat(cd.base_date))
    cd.lunar_month, cd.lunar_day, cd.lunar_text = (lunar["lunar_month"],
                                                   lunar["lunar_day"], lunar["lunar_text"])
    cd.updated_at = now_str()
    session.add(cd)
    session.flush()
    entry_service._from_countdown(session, cd)
    session.commit()
    session.refresh(cd)
    return ok(countdown_service.out(cd))


@router.delete("/{cd_id}")
def remove(cd_id: int, session: Session = Depends(get_session),
           user: User = Depends(get_current_user)):
    _owned(session, user.id, cd_id)
    info = recycle_service.soft_delete(session, user.id, "countdown", cd_id)
    session.commit()
    return ok(info)


@router.get("/{cd_id}/preview")
def preview(cd_id: int, session: Session = Depends(get_session),
            user: User = Depends(get_current_user)):
    """编辑页用：把农历换算结果与下一次发生日期一起回显，便于一眼核对。"""
    cd = _owned(session, user.id, cd_id)
    nxt = countdown_service.next_occurrence(cd)
    return ok({**countdown_service.out(cd), "lunar_check": cd.lunar_text,
               "next_date": nxt["solar_date"]})
