"""值得记 · 健康：生理周期、亲密记录、睡眠。

隐私口径：
- 所有查询/写入/删除都按 user_id 过滤，跨账号拿 id 一律 404；
- 三类数据都不写条目索引（不进手札流、不参与全局搜索排行），删除即真删；
- 亲密记录只有事实字段，没有任何露骨内容，审核口径与主流健康 App 一致。
"""
import json
import re

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from ..database import get_session
from ..models import CycleRecord, IntimacyRecord, SleepRecord, User
from ..schemas import (CycleCreate, CycleUpdate, IntimacyCreate, IntimacyUpdate,
                       SleepCreate, SleepUpdate)
from ..services import health_service
from ..utils.errors import AppError, Codes, not_found, ok
from ..utils.timeutil import now_str, today_str
from .deps import get_current_user, require_module

router = APIRouter(prefix="/api/health", tags=["health"],
                   dependencies=[Depends(require_module("module_health_enabled"))])

FLOWS = {"light", "medium", "heavy"}
KINDS = {"self", "partner", "multi"}
PROTECTIONS = {"condom", "pill", "none", "na"}


def _bad(msg: str):
    raise AppError(Codes.VALIDATION, msg, status=422)


def _owned(session: Session, model, user_id: int, row_id: int):
    row = session.get(model, row_id)
    if row is None or row.user_id != user_id:
        raise not_found("这条记录不存在或已删除")
    return row


def _check_cycle(start: str, end: str | None) -> None:
    if end and end < start:
        _bad("结束日期不能早于开始日期")
    if start > today_str():
        _bad("经期开始日期不能晚于今天")


def _check_intimacy(kind: str, protection: str) -> None:
    if kind not in KINDS:
        _bad("类型只能是 自己 / 两人 / 多人")
    if protection not in PROTECTIONS:
        _bad("保护措施取值不合法")


# ---------- 月历总览 ----------

@router.get("/overview")
def overview(month: str | None = Query(default=None),
             session: Session = Depends(get_session),
             user: User = Depends(get_current_user)):
    """按月份把三类记录摊成日期标识，供日历打点。"""
    month = month or today_str()[:7]
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month):
        _bad("月份格式应为 YYYY-MM")
    cycles = session.exec(select(CycleRecord)
                          .where(CycleRecord.user_id == user.id)).all()
    intimacies = session.exec(select(IntimacyRecord)
                              .where(IntimacyRecord.user_id == user.id)).all()
    sleeps = session.exec(select(SleepRecord)
                          .where(SleepRecord.user_id == user.id)).all()
    return ok(health_service.month_overview(cycles, intimacies, sleeps, month))


# ---------- 周期 ----------

@router.get("/cycle")
def cycle_list(session: Session = Depends(get_session),
               user: User = Depends(get_current_user)):
    rows = session.exec(select(CycleRecord)
                        .where(CycleRecord.user_id == user.id)).all()
    data = health_service.cycle_prediction(rows)
    return ok(data)


@router.post("/cycle")
def cycle_create(body: CycleCreate, session: Session = Depends(get_session),
                 user: User = Depends(get_current_user)):
    start = body.start_date.isoformat()
    end = body.end_date.isoformat() if body.end_date else None
    _check_cycle(start, end)
    if body.flow not in FLOWS:
        _bad("流量只能选 少量 / 中等 / 较多")
    exists = session.exec(select(CycleRecord)
                          .where(CycleRecord.user_id == user.id)
                          .where(CycleRecord.start_date == start)).first()
    if exists:
        raise AppError(Codes.VALIDATION, "这一天已经记过经期了", status=409)

    row = CycleRecord(user_id=user.id, start_date=start, end_date=end,
                      flow=body.flow, note=(body.note or "").strip() or None,
                      symptoms=json.dumps(body.symptoms[:8], ensure_ascii=False)
                      if body.symptoms else None)
    session.add(row)
    session.commit()
    session.refresh(row)
    return ok(health_service.cycle_out(row))


@router.patch("/cycle/{row_id}")
def cycle_update(row_id: int, body: CycleUpdate,
                 session: Session = Depends(get_session),
                 user: User = Depends(get_current_user)):
    row = _owned(session, CycleRecord, user.id, row_id)
    data = body.model_dump(exclude_unset=True)
    start = data["start_date"].isoformat() if data.get("start_date") else row.start_date
    if "end_date" in data:
        end = data["end_date"].isoformat() if data["end_date"] else None
    else:
        end = row.end_date
    _check_cycle(start, end)
    if "flow" in data:
        if data["flow"] not in FLOWS:
            _bad("流量只能选 少量 / 中等 / 较多")
        row.flow = data["flow"]
    if "symptoms" in data:
        row.symptoms = (json.dumps(data["symptoms"][:8], ensure_ascii=False)
                        if data["symptoms"] else None)
    if "note" in data:
        row.note = (data["note"] or "").strip() or None
    row.start_date, row.end_date = start, end
    row.updated_at = now_str()
    session.add(row)
    session.commit()
    session.refresh(row)
    return ok(health_service.cycle_out(row))


@router.delete("/cycle/{row_id}")
def cycle_delete(row_id: int, session: Session = Depends(get_session),
                 user: User = Depends(get_current_user)):
    session.delete(_owned(session, CycleRecord, user.id, row_id))
    session.commit()
    return ok({"id": row_id})


# ---------- 亲密 ----------

@router.get("/intimacy")
def intimacy_list(limit: int = Query(default=60, ge=1, le=200),
                  session: Session = Depends(get_session),
                  user: User = Depends(get_current_user)):
    rows = session.exec(select(IntimacyRecord)
                        .where(IntimacyRecord.user_id == user.id)).all()
    items = [health_service.intimacy_out(r) for r in rows]
    items.sort(key=lambda x: (x["happen_date"], x["happen_time"] or ""), reverse=True)
    return ok({
        "items": items[:limit],
        "stats": health_service.intimacy_stats(items),
        "kind_options": [{"value": k, "label": v}
                         for k, v in health_service.KIND_LABELS.items()],
        "protection_options": [{"value": k, "label": v}
                               for k, v in health_service.PROTECTION_LABELS.items()],
    })


@router.post("/intimacy")
def intimacy_create(body: IntimacyCreate, session: Session = Depends(get_session),
                    user: User = Depends(get_current_user)):
    _check_intimacy(body.kind, body.protection)
    if body.happen_date.isoformat() > today_str():
        _bad("日期不能晚于今天")
    row = IntimacyRecord(
        user_id=user.id, happen_date=body.happen_date.isoformat(),
        happen_time=body.happen_time,
        kind=body.kind,
        # 单人不涉及保护措施，统一存 na，避免统计口径混乱
        protection="na" if body.kind == "self" else body.protection,
        note=(body.note or "").strip() or None)
    session.add(row)
    session.commit()
    session.refresh(row)
    return ok(health_service.intimacy_out(row))


@router.patch("/intimacy/{row_id}")
def intimacy_update(row_id: int, body: IntimacyUpdate,
                    session: Session = Depends(get_session),
                    user: User = Depends(get_current_user)):
    row = _owned(session, IntimacyRecord, user.id, row_id)
    data = body.model_dump(exclude_unset=True)
    kind = data.get("kind", row.kind)
    protection = data.get("protection", row.protection)
    _check_intimacy(kind, protection)
    if "happen_date" in data:
        if data["happen_date"] is None:
            _bad("日期不能为空")
        if data["happen_date"].isoformat() > today_str():
            _bad("日期不能晚于今天")
        row.happen_date = data["happen_date"].isoformat()
    if "happen_time" in data:
        row.happen_time = data["happen_time"]
    if "note" in data:
        row.note = (data["note"] or "").strip() or None
    row.kind = kind
    row.protection = "na" if kind == "self" else protection
    row.updated_at = now_str()
    session.add(row)
    session.commit()
    session.refresh(row)
    return ok(health_service.intimacy_out(row))


@router.delete("/intimacy/{row_id}")
def intimacy_delete(row_id: int, session: Session = Depends(get_session),
                    user: User = Depends(get_current_user)):
    session.delete(_owned(session, IntimacyRecord, user.id, row_id))
    session.commit()
    return ok({"id": row_id})


# ---------- 睡眠 ----------

@router.get("/sleep")
def sleep_list(limit: int = Query(default=60, ge=1, le=200),
               session: Session = Depends(get_session),
               user: User = Depends(get_current_user)):
    rows = session.exec(select(SleepRecord)
                        .where(SleepRecord.user_id == user.id)).all()
    items = [health_service.sleep_out(r) for r in rows]
    items.sort(key=lambda x: x["sleep_date"], reverse=True)
    return ok({
        "items": items[:limit],
        "stats": health_service.sleep_stats(items),
        "quality_options": [{"value": k, "label": v}
                            for k, v in health_service.QUALITY_LABELS.items()],
    })


@router.post("/sleep")
def sleep_create(body: SleepCreate, session: Session = Depends(get_session),
                 user: User = Depends(get_current_user)):
    sleep_date = body.sleep_date.isoformat()
    if sleep_date > today_str():
        _bad("日期不能晚于今天")
    try:
        minutes = health_service.sleep_minutes(body.bed_time, body.wake_time)
    except ValueError as exc:
        _bad(str(exc))
    dup = session.exec(select(SleepRecord)
                       .where(SleepRecord.user_id == user.id)
                       .where(SleepRecord.sleep_date == sleep_date)).first()
    if dup:
        raise AppError(Codes.VALIDATION, "这一天已经记过睡眠了，直接编辑那条即可",
                       status=409)

    row = SleepRecord(user_id=user.id, sleep_date=sleep_date,
                      bed_time=body.bed_time, wake_time=body.wake_time,
                      duration_min=minutes, quality=body.quality,
                      note=(body.note or "").strip() or None)
    session.add(row)
    session.commit()
    session.refresh(row)
    return ok(health_service.sleep_out(row))


@router.patch("/sleep/{row_id}")
def sleep_update(row_id: int, body: SleepUpdate,
                 session: Session = Depends(get_session),
                 user: User = Depends(get_current_user)):
    row = _owned(session, SleepRecord, user.id, row_id)
    data = body.model_dump(exclude_unset=True)
    if "sleep_date" in data:
        if data["sleep_date"] is None:
            _bad("日期不能为空")
        if data["sleep_date"].isoformat() > today_str():
            _bad("日期不能晚于今天")
        row.sleep_date = data["sleep_date"].isoformat()
    if "bed_time" in data:
        row.bed_time = data["bed_time"]
    if "wake_time" in data:
        row.wake_time = data["wake_time"]
    if "quality" in data:
        row.quality = data["quality"]
    if "note" in data:
        row.note = (data["note"] or "").strip() or None
    try:
        row.duration_min = health_service.sleep_minutes(row.bed_time, row.wake_time)
    except ValueError as exc:
        _bad(str(exc))
    row.updated_at = now_str()
    session.add(row)
    session.commit()
    session.refresh(row)
    return ok(health_service.sleep_out(row))


@router.delete("/sleep/{row_id}")
def sleep_delete(row_id: int, session: Session = Depends(get_session),
                 user: User = Depends(get_current_user)):
    session.delete(_owned(session, SleepRecord, user.id, row_id))
    session.commit()
    return ok({"id": row_id})
