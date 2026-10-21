"""健康模块的纯计算逻辑：周期预测、睡眠时长、统计。

预测口径跟主流经期 App 一致，且刻意保守：
- 相邻两次开始日期间隔 15~60 天才算有效样本，最多取最近 6 次求平均；
- 平均周期夹在 21~45 天，默认 28；经期长度夹在 2~10 天，默认 5；
- 排卵日按「下次月经前 14 天」估算，易孕期 = 排卵日前 5 天到后 1 天；
- 所有结果都标注为「预计」，不做医疗建议。
"""
import json
from datetime import date, timedelta

DEFAULT_CYCLE = 28
DEFAULT_PERIOD = 5

FLOW_LABELS = {"light": "少量", "medium": "中等", "heavy": "较多"}
KIND_LABELS = {"self": "自己", "partner": "两人", "multi": "多人"}
PROTECTION_LABELS = {"condom": "避孕套", "pill": "避孕药",
                     "none": "无保护", "na": "未记录"}
SYMPTOM_OPTIONS = ["痛经", "腰酸", "情绪波动", "头痛", "疲惫", "长痘", "胸部胀痛"]
QUALITY_LABELS = {1: "很差", 2: "一般", 3: "还行", 4: "不错", 5: "很香"}


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def parse_clock(value: str) -> tuple[int, int]:
    """'23:30' → (23, 30)；格式不合法抛 ValueError。"""
    parts = (value or "").strip().split(":")
    if len(parts) != 2:
        raise ValueError("时间格式应为 HH:MM")
    hour, minute = int(parts[0]), int(parts[1])
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError("时间超出范围")
    return hour, minute


def sleep_minutes(bed_time: str, wake_time: str) -> int:
    """跨午夜按次日算：23:30 → 07:10 = 460 分钟。"""
    bh, bm = parse_clock(bed_time)
    wh, wm = parse_clock(wake_time)
    bed, wake = bh * 60 + bm, wh * 60 + wm
    if wake <= bed:
        wake += 24 * 60
    delta = wake - bed
    if delta <= 0 or delta >= 24 * 60:
        raise ValueError("入睡与起床时间不能相同，睡眠时长需在 24 小时以内")
    return delta


def _avg(values: list[int], default: int, lo: int, hi: int) -> int:
    values = [v for v in values if v]
    if not values:
        return default
    return max(lo, min(hi, round(sum(values) / len(values))))


def cycle_out(r: "object") -> dict:
    start = parse_date(r.start_date)
    end = parse_date(r.end_date) if r.end_date else None
    days = (end - start).days + 1 if end else None
    return {
        "id": r.id, "start_date": r.start_date, "end_date": r.end_date,
        "flow": r.flow, "flow_label": FLOW_LABELS.get(r.flow, r.flow),
        "symptoms": json.loads(r.symptoms or "[]"),
        "note": r.note, "days": days, "ongoing": end is None,
        "created_at": r.created_at,
    }


def cycle_prediction(records: list) -> dict:
    """records：本人的全部经期记录（顺序不限）。返回今日状态 + 预测。"""
    today = date.today()
    rows = sorted(records, key=lambda r: r.start_date)
    history = [cycle_out(r) for r in reversed(rows)]

    if not rows:
        return {
            "has_data": False, "cycle_len": DEFAULT_CYCLE,
            "period_len": DEFAULT_PERIOD, "history": [],
            "phase": "none", "phase_label": "还没记录",
            "tip": "记下最近一次经期，就能开始预测。",
            "symptom_options": SYMPTOM_OPTIONS,
        }

    starts = [parse_date(r.start_date) for r in rows]
    intervals = [(b - a).days for a, b in zip(starts, starts[1:])]
    cycle_len = _avg([d for d in intervals[-6:] if 15 <= d <= 60],
                     DEFAULT_CYCLE, 21, 45)
    lengths = [(parse_date(r.end_date) - parse_date(r.start_date)).days + 1
               for r in rows if r.end_date]
    period_len = _avg([d for d in lengths[-6:] if 1 <= d <= 12],
                      DEFAULT_PERIOD, 2, 10)

    last_start = starts[-1]
    last = rows[-1]
    # 进行中的经期还没结束，按平均经期长度估一个结束日，方便展示
    period_end = (parse_date(last.end_date) if last.end_date
                  else last_start + timedelta(days=period_len - 1))
    next_start = last_start + timedelta(days=cycle_len)
    late_days = max(0, (today - next_start).days)
    days_left = (next_start - today).days

    ovulation = next_start - timedelta(days=14)
    fertile_start = ovulation - timedelta(days=5)
    fertile_end = ovulation + timedelta(days=1)

    if last_start <= today <= period_end:
        phase, phase_label = "period", f"经期第 {(today - last_start).days + 1} 天"
        tip = "这几天的预测都不用太当真，好好休息。"
    elif today < next_start and fertile_start <= today <= fertile_end:
        phase, phase_label = "fertile", "易孕期"
        tip = f"易孕期预计到 {fertile_end.isoformat()}，排卵日约 {ovulation.isoformat()}。"
    elif today < next_start:
        phase = "safe" if today < fertile_start else "luteal"
        phase_label = "相对安全期" if phase == "safe" else "黄体期"
        tip = ("离下次月经还早，适合安排出行和运动。"
               if phase == "safe"
               else "黄体期容易疲惫、情绪波动，早点睡。")
    else:
        phase, phase_label = "late", f"预计推迟 {late_days} 天"
        tip = "周期受作息、压力影响很大，晚几天很常见；连续推迟建议记录观察。"

    return {
        "has_data": True,
        "cycle_len": cycle_len, "period_len": period_len,
        "last_start": last_start.isoformat(),
        "cycle_day": (today - last_start).days + 1,
        "period_end": period_end.isoformat(),
        "ongoing": last.end_date is None,
        "next_start": next_start.isoformat(),
        "days_left": days_left, "late_days": late_days,
        "ovulation": ovulation.isoformat(),
        "fertile_start": fertile_start.isoformat(),
        "fertile_end": fertile_end.isoformat(),
        "phase": phase, "phase_label": phase_label, "tip": tip,
        "avg_interval": cycle_len,
        "history": history,
        "symptom_options": SYMPTOM_OPTIONS,
    }


def intimacy_out(r: "object") -> dict:
    return {
        "id": r.id, "happen_date": r.happen_date, "happen_time": r.happen_time,
        "kind": r.kind, "kind_label": KIND_LABELS.get(r.kind, r.kind),
        "protection": r.protection,
        "protection_label": PROTECTION_LABELS.get(r.protection, r.protection),
        "note": r.note, "created_at": r.created_at,
    }


def intimacy_stats(items: list) -> dict:
    """统计只看最近 30 天，避免把陈年数据混进「本月」。"""
    today = date.today()
    month_prefix = today.isoformat()[:7]
    since = (today - timedelta(days=29)).isoformat()
    this_month = [i for i in items if i["happen_date"].startswith(month_prefix)]
    recent = [i for i in items if i["happen_date"] >= since]
    by_kind = {k: sum(1 for i in recent if i["kind"] == k) for k in KIND_LABELS}
    last = items[0]["happen_date"] if items else None
    return {
        "month_count": len(this_month),
        "recent_count": len(recent),
        "by_kind": by_kind,
        "last_date": last,
        "days_since": (today - parse_date(last)).days if last else None,
        "protected_count": sum(1 for i in recent
                               if i["protection"] in ("condom", "pill")),
    }


def sleep_out(r: "object") -> dict:
    minutes = r.duration_min
    return {
        "id": r.id, "sleep_date": r.sleep_date,
        "bed_time": r.bed_time, "wake_time": r.wake_time,
        "duration_min": minutes,
        "hours_text": (f"{minutes // 60} 小时 {minutes % 60} 分"
                       if minutes % 60 else f"{minutes // 60} 小时"),
        "quality": r.quality,
        "quality_label": QUALITY_LABELS.get(r.quality, str(r.quality)),
        "note": r.note, "created_at": r.created_at,
    }


def sleep_stats(items: list) -> dict:
    """items 已按日期倒序；近 7 条算平均，并给出迷你柱状图数据。"""
    last7 = items[:7]
    durations = [i["duration_min"] for i in last7]
    qualities = [i["quality"] for i in last7]
    return {
        "avg_minutes": round(sum(durations) / len(durations)) if durations else 0,
        "avg_quality": round(sum(qualities) / len(qualities), 1) if qualities else 0,
        "count": len(items),
        "week": list(reversed([{"date": i["sleep_date"], "minutes": i["duration_min"],
                                "quality": i["quality"]} for i in last7])),
    }


def month_overview(cycles: list, intimacies: list, sleeps: list,
                   month: str) -> dict:
    """日历总览：把记录摊到每一天，供前端按日期打标识。

    - 经期按实际区间展开，进行中的按平均经期长度估到「今天」为止；
    - 亲密/睡眠按日期归并；
    - 预测只给一条「下次经期 + 易孕期」，前端按需在当月裁剪显示。
    """
    first = parse_date(month + "-01")
    nxt = (date(first.year + 1, 1, 1) if first.month == 12
           else date(first.year, first.month + 1, 1))
    last = nxt - timedelta(days=1)
    today = date.today()

    pred = cycle_prediction(cycles) if cycles else None
    period_len = pred["period_len"] if pred else DEFAULT_PERIOD

    cycle_days = []
    for r in sorted(cycles, key=lambda r: r.start_date):
        start = parse_date(r.start_date)
        if r.end_date:
            end = parse_date(r.end_date)
        else:
            end = min(today, start + timedelta(days=period_len - 1))
        if end < start:
            end = start
        lo, hi = max(start, first), min(end, last)
        if lo > hi:
            continue
        symptoms = json.loads(r.symptoms or "[]")
        for offset in range((hi - lo).days + 1):
            day = lo + timedelta(days=offset)
            cycle_days.append({
                "date": day.isoformat(), "record_id": r.id,
                "flow": r.flow, "flow_label": FLOW_LABELS.get(r.flow, r.flow),
                "day_index": (day - start).days + 1,
                "ongoing": r.end_date is None,
                "symptoms": symptoms, "note": r.note,
                "start_date": r.start_date, "end_date": r.end_date,
            })

    by_intimacy: dict[str, dict] = {}
    for r in intimacies:
        if not (first.isoformat() <= r.happen_date <= last.isoformat()):
            continue
        bucket = by_intimacy.setdefault(
            r.happen_date, {"date": r.happen_date, "count": 0, "items": []})
        bucket["count"] += 1
        bucket["items"].append(intimacy_out(r))
    for bucket in by_intimacy.values():
        bucket["items"].sort(key=lambda x: x["happen_time"] or "")

    sleep_days = []
    for r in sleeps:
        if not (first.isoformat() <= r.sleep_date <= last.isoformat()):
            continue
        item = sleep_out(r)
        item["date"] = r.sleep_date
        sleep_days.append(item)
    sleep_days.sort(key=lambda x: x["date"])

    predicted = None
    if pred and pred.get("has_data"):
        predicted = {
            "cycle_len": pred["cycle_len"], "period_len": pred["period_len"],
            "period_start": pred["next_start"],
            "period_end": (parse_date(pred["next_start"])
                           + timedelta(days=pred["period_len"] - 1)).isoformat(),
            "fertile_start": pred["fertile_start"],
            "fertile_end": pred["fertile_end"],
            "ovulation": pred["ovulation"],
        }

    durations = [s["duration_min"] for s in sleep_days]
    qualities = [s["quality"] for s in sleep_days]
    return {
        "month": month, "today": today.isoformat(),
        "cycle_days": cycle_days,
        "intimacy_days": sorted(by_intimacy.values(), key=lambda x: x["date"]),
        "sleep_days": sleep_days,
        "predicted": predicted,
        "stats": {
            "cycle_days": len(cycle_days),
            "intimacy_count": sum(b["count"] for b in by_intimacy.values()),
            "sleep_count": len(sleep_days),
            "avg_minutes": round(sum(durations) / len(durations)) if durations else 0,
            "avg_quality": round(sum(qualities) / len(qualities), 1) if qualities else 0,
        },
    }
