"""账本服务（PRD M2）：记一笔、月视图、分类统计。

金额口径：库里一律存正数，方向由 direction 表达；汇总时支出取负号，
收入取正号。结余 = 收入 − 支出。
"""
import json
from typing import Optional

from sqlmodel import Session, select

from ..models import LedgerCategory, LedgerRecord
from ..utils.timeutil import now_str

# 预置分类（PRD §M2 字段表）：首次进入账本时懒创建
PRESET = [
    ("餐饮", "🍜"), ("交通", "🚇"), ("居住", "🏠"), ("购物", "🛒"),
    ("人情", "🎁"), ("娱乐", "🎮"), ("医疗", "💊"), ("学习", "📚"), ("其他", "📦"),
]
CUSTOM_LIMIT = 20


def ensure_categories(session: Session, user_id: int) -> list[LedgerCategory]:
    rows = session.exec(select(LedgerCategory)
                        .where(LedgerCategory.user_id == user_id)
                        .order_by(LedgerCategory.sort)).all()
    if rows:
        return rows
    for i, (name, emoji) in enumerate(PRESET):
        session.add(LedgerCategory(user_id=user_id, name=name, emoji=emoji,
                                   is_preset=1, sort=i))
    session.commit()
    return session.exec(select(LedgerCategory)
                        .where(LedgerCategory.user_id == user_id)
                        .order_by(LedgerCategory.sort)).all()


def category_out(c: LedgerCategory) -> dict:
    return {"id": c.id, "name": c.name, "emoji": c.emoji,
            "is_preset": bool(c.is_preset), "sort": c.sort}


def add_category(session: Session, user_id: int, name: str, emoji: str) -> LedgerCategory:
    from ..utils.errors import AppError, Codes
    ensure_categories(session, user_id)
    name = (name or "").strip()
    if not name:
        raise AppError(Codes.VALIDATION, "分类名不能为空", status=422)
    if len(name) > 10:
        raise AppError(Codes.VALIDATION, "分类名最多 10 个字", status=422)
    exists = session.exec(select(LedgerCategory)
                          .where(LedgerCategory.user_id == user_id)
                          .where(LedgerCategory.name == name)).first()
    if exists is not None:
        raise AppError(Codes.VALIDATION, "该分类已存在", status=422)
    customs = session.exec(select(LedgerCategory)
                           .where(LedgerCategory.user_id == user_id)
                           .where(LedgerCategory.is_preset == 0)).all()
    if len(customs) >= CUSTOM_LIMIT:
        raise AppError(Codes.VALIDATION, f"自定义分类最多 {CUSTOM_LIMIT} 个", status=422)
    c = LedgerCategory(user_id=user_id, name=name, emoji=emoji or "📦",
                       is_preset=0, sort=100 + len(customs))
    session.add(c)
    session.commit()
    session.refresh(c)
    return c


def delete_category(session: Session, user_id: int, cat_id: int) -> dict:
    """删除自定义分类：已归属该分类的账目自动落入「其他」，不阻断删除。

    预置分类与他人分类不可删（deleted=False），前端据此提示。
    """
    c = session.get(LedgerCategory, cat_id)
    if c is None or c.user_id != user_id or c.is_preset:
        return {"deleted": False, "moved_to_other": 0}
    name = c.name
    rows = session.exec(select(LedgerRecord)
                        .where(LedgerRecord.user_id == user_id)
                        .where(LedgerRecord.category == name)).all()
    for r in rows:
        r.category = "其他"
        r.updated_at = now_str()
        session.add(r)
    session.delete(c)
    session.commit()
    return {"deleted": True, "moved_to_other": len(rows)}


def touch_category(session: Session, user_id: int, name: str) -> None:
    """记录上次使用时间 → 快速记一笔默认选中「上一次使用的分类」。

    这里用带微秒的时间戳（与其他表的秒级口径不同）：连续记几笔时若只有秒级精度，
    同秒内的记录会并列，取「最近使用」就会退化成按分类顺序，默认选中项不稳定。
    该字段只用于内部排序比较，不对外展示。
    """
    c = session.exec(select(LedgerCategory)
                     .where(LedgerCategory.user_id == user_id)
                     .where(LedgerCategory.name == name)).first()
    if c is not None:
        from datetime import datetime
        c.last_used_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        session.add(c)


def record_out(r: LedgerRecord) -> dict:
    return {"id": r.id, "direction": r.direction, "amount": round(r.amount, 2),
            "category": r.category, "account": r.account, "occurred_on": r.occurred_on,
            "note": r.note, "media_id": r.media_id, "created_at": r.created_at}


def list_records(session: Session, user_id: int, month: Optional[str] = None,
                 direction: Optional[str] = None, category: Optional[str] = None,
                 limit: int = 100) -> dict:
    stmt = select(LedgerRecord).where(LedgerRecord.user_id == user_id) \
                               .where(LedgerRecord.status == "normal")
    if month:
        stmt = stmt.where(LedgerRecord.occurred_on.startswith(month))
    if direction:
        stmt = stmt.where(LedgerRecord.direction == direction)
    if category:
        stmt = stmt.where(LedgerRecord.category == category)
    rows = session.exec(stmt.order_by(LedgerRecord.occurred_on.desc(),
                                      LedgerRecord.id.desc()).limit(limit)).all()
    days: dict[str, list[dict]] = {}
    for r in rows:
        days.setdefault(r.occurred_on, []).append(record_out(r))
    return {"items": [record_out(r) for r in rows],
            "days": [{"date": d, "items": v} for d, v in days.items()]}


def month_key(offset: int = 0, base_month: Optional[str] = None) -> str:
    """相对某月的偏移（offset=-1 表示上个月）。"""
    from datetime import date
    if base_month:
        y, m = int(base_month[:4]), int(base_month[5:7])
    else:
        y, m = date.today().year, date.today().month
    idx = y * 12 + (m - 1) + offset
    return f"{idx // 12:04d}-{idx % 12 + 1:02d}"


def summary(session: Session, user_id: int, month: Optional[str] = None) -> dict:
    month = month or month_key()
    rows = session.exec(select(LedgerRecord)
                        .where(LedgerRecord.user_id == user_id)
                        .where(LedgerRecord.status == "normal")
                        .where(LedgerRecord.occurred_on.startswith(month))).all()
    expense = sum(r.amount for r in rows if r.direction == "expense")
    income = sum(r.amount for r in rows if r.direction == "income")

    prev = month_key(-1, month)
    prev_rows = session.exec(select(LedgerRecord)
                             .where(LedgerRecord.user_id == user_id)
                             .where(LedgerRecord.status == "normal")
                             .where(LedgerRecord.occurred_on.startswith(prev))).all()
    prev_expense = sum(r.amount for r in prev_rows if r.direction == "expense")

    return {"month": month, "expense": round(expense, 2), "income": round(income, 2),
            "balance": round(income - expense, 2), "count": len(rows),
            "prev_expense": round(prev_expense, 2),
            "expense_delta": round(expense - prev_expense, 2),
            "has_prev": bool(prev_rows)}


def category_stats(session: Session, user_id: int, month: Optional[str] = None) -> list[dict]:
    month = month or month_key()
    rows = session.exec(select(LedgerRecord)
                        .where(LedgerRecord.user_id == user_id)
                        .where(LedgerRecord.status == "normal")
                        .where(LedgerRecord.direction == "expense")
                        .where(LedgerRecord.occurred_on.startswith(month))).all()
    cats = {c.name: c for c in ensure_categories(session, user_id)}
    agg: dict[str, float] = {}
    for r in rows:
        agg[r.category] = agg.get(r.category, 0) + r.amount
    total = sum(agg.values()) or 1
    out = [{"name": k, "emoji": cats[k].emoji if k in cats else "📦",
            "amount": round(v, 2), "percent": round(v / total * 100, 1)}
           for k, v in sorted(agg.items(), key=lambda x: -x[1])]
    return out


def monthly_trend(session: Session, user_id: int, months: int = 6) -> list[dict]:
    """最近 N 个月的支出/收入（月对月对比，PRD §M2 二级统计页）。"""
    result = []
    for i in range(months - 1, -1, -1):
        m = month_key(-i)
        s = summary(session, user_id, m)
        result.append({"month": m, "expense": s["expense"], "income": s["income"]})
    return result


def last_used_category(session: Session, user_id: int) -> Optional[dict]:
    cats = ensure_categories(session, user_id)
    used = [c for c in cats if c.last_used_at]
    if used:
        c = max(used, key=lambda x: x.last_used_at)
        return category_out(c)
    return category_out(cats[0]) if cats else None


def tags_json(extra: dict) -> str:
    return json.dumps(extra, ensure_ascii=False)
