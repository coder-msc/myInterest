"""日子服务（PRD M5）：重复规则推进 + 农历换算 + 状态判定。

农历换算是本模块唯一的「算错就会误事」的地方（生日、纪念日），因此：
- 本地用 lunardate 纯算法换算，不依赖网络；
- 出参同时给农历原文与换算后的公历日期，让用户一眼核对（PRD §M5 说明）。
"""
import calendar
import json
from datetime import date, timedelta
from typing import Optional

from ..models import Countdown

LUNAR_MONTHS = ["正月", "二月", "三月", "四月", "五月", "六月",
                "七月", "八月", "九月", "十月", "冬月", "腊月"]
LUNAR_DAYS = ["初一", "初二", "初三", "初四", "初五", "初六", "初七", "初八", "初九", "初十",
              "十一", "十二", "十三", "十四", "十五", "十六", "十七", "十八", "十九", "二十",
              "廿一", "廿二", "廿三", "廿四", "廿五", "廿六", "廿七", "廿八", "廿九", "三十"]
REPEAT_RULES = ("once", "yearly", "monthly", "yearly_lunar", "anniversary")
REMIND_CHOICES = (30, 7, 1, 0)


def lunar_text(month: int, day: int) -> str:
    if not (1 <= month <= 12 and 1 <= day <= 30):
        return ""
    return LUNAR_MONTHS[month - 1] + LUNAR_DAYS[day - 1]


def solar_to_lunar(d: date) -> tuple[int, int, str]:
    """公历 → (农历月, 农历日, 原文)。闰月按本月处理（对生日足够）。"""
    try:
        from lunardate import LunarDate
        ld = LunarDate.from_solar_date(d.year, d.month, d.day)
        return ld.month, ld.day, lunar_text(ld.month, ld.day)
    except Exception:
        return 0, 0, ""


def lunar_to_solar(lunar_month: int, lunar_day: int, year: int) -> Optional[date]:
    """农历（某农历年）→ 公历。该年此月无三十时回退到廿九。"""
    try:
        from lunardate import LunarDate
    except Exception:
        return None
    for day in (lunar_day, 29):
        try:
            return LunarDate(year, lunar_month, day).to_solar_date()
        except Exception:
            continue
    return None


def _month_day(year: int, month: int, day: int) -> date:
    """构造公历日期；该月无此日时取该月最后一天（PRD：29/30/31 规则）。"""
    last = calendar.monthrange(year, month)[1]
    return date(year, month, min(day, last))


def _add_month(year: int, month: int, delta: int) -> tuple[int, int]:
    idx = year * 12 + (month - 1) + delta
    return idx // 12, idx % 12 + 1


def next_occurrence(cd: Countdown, today: Optional[date] = None) -> dict:
    """计算该日子的下一次发生日期与展示口径。"""
    today = today or date.today()
    try:
        base = date.fromisoformat(cd.base_date)
    except Exception:
        base = today
    rule = cd.repeat_rule if cd.repeat_rule in REPEAT_RULES else "once"

    days_since: Optional[int] = None
    if rule == "once":
        target, year_no, is_past = base, None, base < today
    elif rule == "yearly":
        target = _month_day(today.year, base.month, base.day)
        if target < today:
            target = _month_day(today.year + 1, base.month, base.day)
        year_no = target.year - base.year + 1
        is_past = False
    elif rule == "monthly":
        target = _month_day(today.year, today.month, base.day)
        if target < today:
            y, m = _add_month(today.year, today.month, 1)
            target = _month_day(y, m, base.day)
        year_no = None
        is_past = False
    elif rule == "anniversary":
        # 纪念日：base 是起点（通常在过去），主口径是「已经多久」；
        # 同时仍算出下一个周年日，供月历标记与提醒使用。
        target = _month_day(today.year, base.month, base.day)
        if target < today:
            target = _month_day(today.year + 1, base.month, base.day)
        years = today.year - base.year
        if (today.month, today.day) < (base.month, base.day):
            years -= 1
        year_no = max(0, years)
        days_since = (today - base).days
        is_past = False
    else:  # yearly_lunar
        lm = cd.lunar_month or base.month
        ld = cd.lunar_day or base.day
        target = lunar_to_solar(lm, ld, today.year) or _month_day(today.year, base.month, base.day)
        if target < today:
            target = lunar_to_solar(lm, ld, today.year + 1) or _month_day(
                today.year + 1, base.month, base.day)
        year_no = target.year - base.year + 1
        is_past = False

    days_left = (target - today).days
    if rule == "anniversary" and days_since is not None and days_since >= 0:
        if days_since == 0:
            label, state = "从今天开始", "today"
        elif year_no and year_no >= 1:
            label, state = f"已经 {year_no} 周年", "anniversary"
        else:
            label, state = f"已经 {days_since} 天", "anniversary"
    elif rule == "once" and is_past:
        label = f"已过去 {-days_left} 天"
        state = "past"
    elif days_left == 0:
        label = "就是今天"
        state = "today"
    elif days_left <= 7:
        label = f"还有 {days_left} 天"
        state = "urgent"
    elif days_left <= 30:
        label = f"还有 {days_left} 天"
        state = "near"
    else:
        label = f"还有 {days_left} 天"
        state = "normal"

    return {
        "solar_date": target.isoformat(),
        "days_left": days_left,
        "state": state,
        "label": label,
        "year_no": year_no,
        "is_past": rule == "once" and is_past,
        "days_since": days_since,
        "repeat_rule": rule,
    }


def effective_offsets(cd: Countdown) -> list[int]:
    """提醒档位（只保留合法值，去重倒序）。"""
    try:
        raw = json.loads(cd.remind_offsets or "[]")
        vals = [int(v) for v in raw if int(v) in REMIND_CHOICES]
    except Exception:
        vals = [7, 0]
    return sorted(set(vals), reverse=True)


def out(cd: Countdown, today: Optional[date] = None) -> dict:
    nxt = next_occurrence(cd, today)
    return {
        "id": cd.id, "name": cd.name, "base_date": cd.base_date,
        "repeat_rule": cd.repeat_rule, "lunar_month": cd.lunar_month,
        "lunar_day": cd.lunar_day, "lunar_text": cd.lunar_text,
        "remind_offsets": effective_offsets(cd), "pinned": bool(cd.pinned),
        "emoji": cd.emoji, "color": cd.color, "note": cd.note,
        "next_date": nxt["solar_date"], "days_left": nxt["days_left"],
        "state": nxt["state"], "state_label": nxt["label"],
        "year_no": nxt["year_no"], "is_past": nxt["is_past"],
        "days_since": nxt["days_since"],
        "created_at": cd.created_at,
    }


def sort_key(item: dict):
    """排序：置顶 → 今天/临近 → 剩余天数；纪念日单独成组；已过去沉底（PRD §M5）。"""
    if item["is_past"]:
        return (3, 0, 0, -item["days_left"])
    if item.get("repeat_rule") == "anniversary":
        return (2, 0 if item["pinned"] else 1, -(item.get("days_since") or 0), 0)
    return (0 if item["pinned"] else 1, 0 if item["days_left"] <= 0 else 1,
            item["days_left"], 0)


def reminder_targets(cd: Countdown, today: date) -> list[int]:
    """今天该触发的档位：days_left 恰好等于某个已选档位。"""
    nxt = next_occurrence(cd, today)
    if nxt["is_past"]:
        return []
    return [d for d in effective_offsets(cd) if d == nxt["days_left"]]


def reminder_text(cd: Countdown, offset: int, nxt: dict) -> tuple[str, str]:
    """站内消息标题与正文（玩梗只在情绪位，日期数字保持克制）。"""
    if offset == 0:
        return f"今天就是「{cd.name}」", f"就是今天，别错过。{cd.note or ''}".strip()
    return (f"还有 {offset} 天：{cd.name}",
            f"{nxt['solar_date']} 就是了，现在准备还来得及。{cd.note or ''}".strip())
