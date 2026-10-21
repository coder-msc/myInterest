"""账本接口（PRD M2）：记一笔、月视图、分类统计。

写入硬约束：主表记录与条目索引必须在同一事务提交（PRD §4.2）。
"""
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from ..database import get_session
from ..models import LedgerRecord, User
from ..schemas import LedgerCategoryIn, LedgerCreate, LedgerUpdate
from ..services import entry_service, ledger_service, media_service, recycle_service
from ..utils.errors import AppError, Codes, not_found, ok
from ..utils.timeutil import now_str
from .deps import get_current_user, require_module

router = APIRouter(prefix="/api/ledger", tags=["ledger"],
                   dependencies=[Depends(require_module("module_ledger_enabled"))])


def _owned(session: Session, user_id: int, record_id: int) -> LedgerRecord:
    r = session.get(LedgerRecord, record_id)
    if r is None or r.user_id != user_id or r.status != "normal":
        raise not_found("这笔记录不存在或已删除")
    return r


@router.get("")
def list_records(month: str | None = Query(default=None, max_length=7),
                 direction: str | None = None,
                 category: str | None = None,
                 limit: int = Query(default=200, ge=1, le=500),
                 session: Session = Depends(get_session),
                 user: User = Depends(get_current_user)):
    ledger_service.ensure_categories(session, user.id)
    data = ledger_service.list_records(session, user.id, month, direction, category, limit)
    data["summary"] = ledger_service.summary(session, user.id, month)
    data["categories"] = [ledger_service.category_out(c)
                          for c in ledger_service.ensure_categories(session, user.id)]
    data["last_category"] = ledger_service.last_used_category(session, user.id)
    return ok(data)


@router.get("/stats")
def stats(month: str | None = None, months: int = Query(default=6, ge=1, le=24),
          session: Session = Depends(get_session),
          user: User = Depends(get_current_user)):
    return ok({"summary": ledger_service.summary(session, user.id, month),
               "categories": ledger_service.category_stats(session, user.id, month),
               "trend": ledger_service.monthly_trend(session, user.id, months)})


@router.post("")
def create(body: LedgerCreate, session: Session = Depends(get_session),
           user: User = Depends(get_current_user)):
    if body.occurred_on > date.today():
        raise AppError(Codes.VALIDATION, "日期不能选未来", status=422)
    if body.media_id:
        media_service.get_owned(session, user.id, body.media_id)  # 校验归属
    r = LedgerRecord(user_id=user.id, direction=body.direction, amount=round(body.amount, 2),
                     category=body.category, account=body.account,
                     occurred_on=body.occurred_on.isoformat(), note=body.note,
                     media_id=body.media_id)
    session.add(r)
    session.flush()  # 拿 id，保证索引与主表同一事务
    if body.media_id:
        media_service.attach(session, user.id, [body.media_id], "ledger", r.id)
    entry_service._from_ledger(session, r)
    ledger_service.touch_category(session, user.id, body.category)
    session.commit()
    session.refresh(r)
    return ok(ledger_service.record_out(r))


@router.patch("/{record_id}")
def update(record_id: int, body: LedgerUpdate, session: Session = Depends(get_session),
           user: User = Depends(get_current_user)):
    r = _owned(session, user.id, record_id)
    data = body.model_dump(exclude_unset=True)
    if "occurred_on" in data and data["occurred_on"]:
        if data["occurred_on"] > date.today():
            raise AppError(Codes.VALIDATION, "日期不能选未来", status=422)
        r.occurred_on = data.pop("occurred_on").isoformat()
    if "media_id" in data:
        mid = data.pop("media_id")
        r.media_id = mid
        if mid:
            media_service.get_owned(session, user.id, mid)
            media_service.attach(session, user.id, [mid], "ledger", r.id)
    for k, v in data.items():
        if v is not None:
            setattr(r, k, v)
    if r.amount <= 0:
        raise AppError(Codes.VALIDATION, "金额必须大于 0", status=422)
    r.updated_at = now_str()
    session.add(r)
    session.flush()
    entry_service._from_ledger(session, r)
    session.commit()
    session.refresh(r)
    return ok(ledger_service.record_out(r))


@router.delete("/{record_id}")
def remove(record_id: int, session: Session = Depends(get_session),
           user: User = Depends(get_current_user)):
    _owned(session, user.id, record_id)
    info = recycle_service.soft_delete(session, user.id, "ledger", record_id)
    session.commit()
    return ok(info)


# ---------- 分类 ----------
@router.get("/categories")
def categories(session: Session = Depends(get_session),
               user: User = Depends(get_current_user)):
    rows = ledger_service.ensure_categories(session, user.id)
    return ok([ledger_service.category_out(c) for c in rows])


@router.post("/categories")
def add_category(body: LedgerCategoryIn, session: Session = Depends(get_session),
                 user: User = Depends(get_current_user)):
    c = ledger_service.add_category(session, user.id, body.name, body.emoji)
    return ok(ledger_service.category_out(c))


@router.delete("/categories/{cat_id}")
def remove_category(cat_id: int, session: Session = Depends(get_session),
                    user: User = Depends(get_current_user)):
    return ok(ledger_service.delete_category(session, user.id, cat_id))


# 说明：动态段路由必须放在所有静态段路由之后，否则 /categories 会被
# /{record_id} 抢先匹配并当成 id 去解析（FastAPI 按声明顺序匹配）。
@router.get("/{record_id}")
def detail(record_id: int, session: Session = Depends(get_session),
           user: User = Depends(get_current_user)):
    """单条详情：手札流从索引点进来时落地到这里（索引 ref_id → 主表记录）。"""
    return ok(ledger_service.record_out(_owned(session, user.id, record_id)))
