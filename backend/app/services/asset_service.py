"""家庭资产服务（PRD M6）。

净值 = 资产合计 − 负债合计，多币种按当日汇率折算人民币后合并。
投资持仓不落新表：由原「攒息」的 holdings + lots 实时汇总估值。
快照只在用户主动「盘点」时生成。
"""
import json
from datetime import date
from typing import Optional

from sqlmodel import Session, select

from ..models import AssetItem, AssetSnapshot, Holding, Lot
from ..services import fx_service
from ..utils.timeutil import now_str
from .lots_service import shares_now

CATEGORY_LABEL = {"cash": "现金与存款", "investment": "投资持仓", "property": "房产",
                  "vehicle": "车辆", "other": "其他资产", "liability": "负债"}
CATEGORY_EMOJI = {"cash": "💰", "investment": "📈", "property": "🏠",
                  "vehicle": "🚗", "other": "🧾", "liability": "💳"}
CURRENCIES = ("CNY", "USD", "HKD")


def item_out(it: AssetItem) -> dict:
    return {"id": it.id, "category": it.category,
            "category_label": CATEGORY_LABEL.get(it.category, it.category),
            "sub_category": it.sub_category, "name": it.name,
            "amount": round(it.amount, 2), "currency": it.currency,
            "note": it.note, "repay_date": it.repay_date,
            "created_at": it.created_at}


def _to_cny(session: Session, amount: float, currency: str, day: str) -> tuple[float, bool]:
    """折算人民币；返回 (金额, 是否用了兜底汇率)。"""
    if currency == "CNY" or not currency:
        return amount, False
    from . import config_service
    try:
        rate = fx_service.get_rate_cny(session, currency, day)
        fallback = config_service.get_float(f"fx_fallback_{currency.lower()}")
        used_fallback = abs(float(rate) - float(fallback)) < 1e-9
        return round(amount * float(rate), 2), used_fallback
    except Exception:
        fb = 7.12 if currency == "USD" else 0.9128
        return round(amount * fb, 2), True


def investment_valuation(session: Session, user_id: int) -> dict:
    """投资持仓估值：股数 × 现价（无现价时用最近买入价兜底），按币种折算 CNY。"""
    holdings = session.exec(select(Holding).where(Holding.user_id == user_id)).all()
    if not holdings:
        return {"has_data": False, "value": 0.0, "count": 0, "estimated_at": None,
                "fallback_fx": False}
    total = 0.0
    fallback_any = False
    for h in holdings:
        lots = session.exec(select(Lot).where(Lot.holding_id == h.id)).all()
        shares = shares_now(lots)
        if shares <= 0:
            continue
        price = h.current_price
        if price is None:
            bought = [l for l in lots if l.direction == "buy"]
            price = bought[-1].price if bought else 0
        value, fb = _to_cny(session, shares * float(price), h.currency,
                            date.today().isoformat())
        total += value
        fallback_any = fallback_any or fb
    return {"has_data": True, "value": round(total, 2), "count": len(holdings),
            "estimated_at": now_str(), "fallback_fx": fallback_any}


def overview(session: Session, user_id: int) -> dict:
    day = date.today().isoformat()
    items = session.exec(select(AssetItem)
                         .where(AssetItem.user_id == user_id)
                         .where(AssetItem.status == "normal")).all()
    groups: dict[str, list[dict]] = {k: [] for k in CATEGORY_LABEL}
    assets_total = 0.0
    liab_total = 0.0
    fallback_any = False
    for it in items:
        cny, fb = _to_cny(session, it.amount, it.currency, day)
        fallback_any = fallback_any or fb
        row = item_out(it)
        row["amount_cny"] = cny
        groups.setdefault(it.category, []).append(row)
        if it.category == "liability":
            liab_total += cny
        else:
            assets_total += cny

    inv = investment_valuation(session, user_id)
    groups["investment"] = [{
        "id": None, "category": "investment", "category_label": "投资持仓",
        "name": f"{inv['count']} 只持仓" if inv["has_data"] else "暂未录入",
        "amount": inv["value"], "amount_cny": inv["value"], "currency": "CNY",
        "has_data": inv["has_data"], "estimated_at": inv["estimated_at"],
        "is_linked": True,
    }]
    if inv["has_data"]:
        assets_total += inv["value"]

    groups_out = []
    for key in ("cash", "investment", "property", "vehicle", "other", "liability"):
        groups_out.append({"category": key, "label": CATEGORY_LABEL[key],
                           "emoji": CATEGORY_EMOJI[key], "items": groups.get(key, [])})

    snapshots = session.exec(select(AssetSnapshot)
                             .where(AssetSnapshot.user_id == user_id)
                             .order_by(AssetSnapshot.snapshot_date)).all()
    last = snapshots[-1] if snapshots else None
    return {
        "net_worth": round(assets_total - liab_total, 2),
        "total_assets": round(assets_total, 2),
        "total_liabilities": round(liab_total, 2),
        "groups": groups_out,
        "investment": inv,
        "fallback_fx": fallback_any,
        "snapshots": [snapshot_out(s) for s in snapshots],
        "last_snapshot": snapshot_out(last) if last else None,
        "has_data": bool(items) or inv["has_data"],
    }


def snapshot_out(s: AssetSnapshot) -> dict:
    return {"id": s.id, "snapshot_date": s.snapshot_date,
            "net_worth": round(s.net_worth, 2),
            "total_assets": round(s.total_assets, 2),
            "total_liabilities": round(s.total_liabilities, 2),
            "created_at": s.created_at}


def take_snapshot(session: Session, user_id: int) -> AssetSnapshot:
    """用户主动盘点：固化当日净值，用于趋势图（系统不自动生成）。

    不 commit：调用方需把快照与条目索引放进同一事务（PRD §4.2 硬约束）。
    """
    ov = overview(session, user_id)
    day = date.today().isoformat()
    row = session.exec(select(AssetSnapshot)
                       .where(AssetSnapshot.user_id == user_id)
                       .where(AssetSnapshot.snapshot_date == day)).first()
    detail = json.dumps([{"category": g["category"],
                          "items": [{"name": i.get("name"), "amount": i.get("amount_cny")}
                                    for i in g["items"]]}
                         for g in ov["groups"]], ensure_ascii=False)
    if row is None:
        row = AssetSnapshot(user_id=user_id, snapshot_date=day)
    row.total_assets = ov["total_assets"]
    row.total_liabilities = ov["total_liabilities"]
    row.net_worth = ov["net_worth"]
    row.detail = detail
    session.add(row)
    session.flush()
    return row


def trend(session: Session, user_id: int) -> list[dict]:
    rows = session.exec(select(AssetSnapshot)
                        .where(AssetSnapshot.user_id == user_id)
                        .order_by(AssetSnapshot.snapshot_date)).all()
    return [snapshot_out(s) for s in rows]


def pending_repay_days(session: Session, user_id: int) -> list[dict]:
    """负债还款日（可一键生成「日子」条目，PRD §M6）。"""
    rows = session.exec(select(AssetItem)
                        .where(AssetItem.user_id == user_id)
                        .where(AssetItem.category == "liability")
                        .where(AssetItem.status == "normal")).all()
    return [{"id": r.id, "name": r.name, "repay_date": r.repay_date}
            for r in rows if r.repay_date]
