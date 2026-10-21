"""值得记 · 待办清单接口：快速添加、编辑、勾选完成、删除。

列表口径：
- 未完成全部返回，由前端按「逾期 / 今天 / 明天 / 以后 / 没定日子」分组；
- 已完成只回最近 30 条，避免清单用久了越拉越长；
- stats 始终按全量统计，不受已完成条数截断影响。
"""
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from ..database import get_session
from ..models import Todo, User
from ..schemas import TodoCreate, TodoUpdate
from ..utils.errors import AppError, Codes, not_found, ok
from ..utils.timeutil import now_str, today_str
from .deps import get_current_user, require_module

router = APIRouter(prefix="/api/todos", tags=["todos"],
                   dependencies=[Depends(require_module("module_todo_enabled"))])

DONE_LIMIT = 30


def _owned(session: Session, user_id: int, todo_id: int) -> Todo:
    t = session.get(Todo, todo_id)
    if t is None or t.user_id != user_id:
        raise not_found("这条待办不存在或已删除")
    return t


def _out(t: Todo) -> dict:
    return {
        "id": t.id, "title": t.title, "note": t.note,
        "due_date": t.due_date, "important": bool(t.important),
        "done": bool(t.done), "done_at": t.done_at,
        "created_at": t.created_at, "updated_at": t.updated_at,
    }


def _open_key(t: Todo):
    """未完成排序：有日期的按日期升序，没日期的沉底；同日期的「重要」优先。"""
    return (1 if not t.due_date else 0, t.due_date or "",
            0 if t.important else 1, t.created_at)


@router.get("")
def listing(include_done: int = Query(default=1, ge=0, le=1),
            session: Session = Depends(get_session),
            user: User = Depends(get_current_user)):
    rows = session.exec(select(Todo).where(Todo.user_id == user.id)).all()
    open_rows = sorted((t for t in rows if not t.done), key=_open_key)
    done_rows = sorted((t for t in rows if t.done),
                       key=lambda t: t.done_at or t.updated_at, reverse=True)

    today = today_str()
    items = [_out(t) for t in open_rows]
    if include_done:
        items.extend(_out(t) for t in done_rows[:DONE_LIMIT])
    return ok({
        "items": items,
        "stats": {
            "open": len(open_rows),
            "done": len(done_rows),
            "today": sum(1 for t in open_rows if t.due_date == today),
            "overdue": sum(1 for t in open_rows if t.due_date and t.due_date < today),
            "total": len(rows),
        },
    })


@router.post("")
def create(body: TodoCreate, session: Session = Depends(get_session),
           user: User = Depends(get_current_user)):
    title = body.title.strip()
    if not title:
        raise AppError(Codes.VALIDATION, "写点什么吧", status=422)
    t = Todo(user_id=user.id, title=title, note=((body.note or "").strip() or None),
             due_date=body.due_date.isoformat() if body.due_date else None,
             important=body.important)
    session.add(t)
    session.commit()
    session.refresh(t)
    return ok(_out(t))


@router.patch("/{todo_id}")
def update(todo_id: int, body: TodoUpdate, session: Session = Depends(get_session),
           user: User = Depends(get_current_user)):
    t = _owned(session, user.id, todo_id)
    data = body.model_dump(exclude_unset=True)

    if "title" in data:
        title = (data["title"] or "").strip()
        if not title:
            raise AppError(Codes.VALIDATION, "标题不能为空", status=422)
        t.title = title
    if "note" in data:
        t.note = (data["note"] or "").strip() or None
    if "due_date" in data:
        t.due_date = data["due_date"].isoformat() if data["due_date"] else None
    if "important" in data:
        t.important = bool(data["important"])
    if "done" in data:
        t.done = bool(data["done"])
        t.done_at = now_str() if t.done else None

    t.updated_at = now_str()
    session.add(t)
    session.commit()
    session.refresh(t)
    return ok(_out(t))


@router.delete("/{todo_id}")
def remove(todo_id: int, session: Session = Depends(get_session),
           user: User = Depends(get_current_user)):
    t = _owned(session, user.id, todo_id)
    session.delete(t)
    session.commit()
    return ok({"id": todo_id})
