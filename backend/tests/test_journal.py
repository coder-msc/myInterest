"""人生手札 API 集成测试：日子 → 账本 → 足迹 → 资产 → 手札流 → 回收站 → 媒体。

重点覆盖 PRD 的三条硬约束：
1. 索引层与主表同事务（手札流条目能点回主记录）；
2. 提醒幂等（同日子同档位同一天只发一条）；
3. 软删除三态与回收站恢复。
"""
from datetime import date, timedelta

from conftest import auth, ensure_security, register

PNG_1PX = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
    "890000000a49444154789c6360000002000100ffff03000006000557bfabd400"
    "00000049454e44ae426082")


# ---------- 日子：五种重复规则 + 农历 ----------
def test_countdown_repeat_rules(client):
    token = register(client, "days_user")
    today = date.today()
    cases = [
        {"name": "一次性", "date": (today + timedelta(days=200)).isoformat(),
         "repeat_rule": "once"},
        {"name": "每年生日", "date": "1998-03-08", "repeat_rule": "yearly"},
        {"name": "每月还卡", "date": "2024-05-20", "repeat_rule": "monthly"},
        {"name": "农历生日", "date": "1998-09-16", "repeat_rule": "yearly_lunar"},
        {"name": "在一起", "date": "2019-09-21", "repeat_rule": "anniversary"},
    ]
    out = {}
    for c in cases:
        r = client.post("/api/countdowns", headers=auth(token), json={
            "name": c["name"], "date": c["date"], "repeat_rule": c["repeat_rule"],
            "remind_offsets": [30, 7, 0], "emoji": "🎂"}).json()
        assert r["code"] == 0, r
        out[c["name"]] = r["data"]

    # 一次性：已过去的一年视为 past
    once_future = client.post("/api/countdowns", headers=auth(token), json={
        "name": "过去的事", "date": "2020-01-01", "repeat_rule": "once"}).json()["data"]
    assert once_future["is_past"] is True and once_future["days_left"] < 0

    # 每年：下一次必在未来 365 天内，且带上第几年
    y = out["每年生日"]
    assert 0 <= y["days_left"] <= 366 and y["year_no"] >= 1
    # 每月：下一次在 31 天内
    m = out["每月还卡"]
    assert 0 <= m["days_left"] <= 31
    # 农历：同时给出农历原文与换算后的公历日期，便于核对
    l = out["农历生日"]
    assert l["lunar_text"] and l["next_date"] >= today.isoformat()
    # 纪念日：正向计数，主口径是「已经 N 周年」，同时仍算出下一个周年日
    a = out["在一起"]
    assert a["state"] == "anniversary" and a["days_since"] > 0
    assert a["year_no"] >= 1 and a["state_label"].startswith("已经")
    assert a["next_date"] > today.isoformat()

    listing = client.get("/api/countdowns", headers=auth(token)).json()["data"]
    assert listing["max_pinned"] == 3
    # 排序：未来的排在已过去的前面
    assert listing["items"][-1]["name"] == "过去的事"

    # 置顶上限 3 个
    ids = [v["id"] for k, v in out.items()]
    for i in ids[:3]:
        assert client.patch(f"/api/countdowns/{i}", headers=auth(token),
                            json={"pinned": True}).json()["code"] == 0
    r = client.patch(f"/api/countdowns/{ids[3]}", headers=auth(token),
                     json={"pinned": True}).json()
    assert r["code"] != 0 and "最多置顶" in r["msg"]


def test_lunar_month_rules(client):
    """农历换算：公历 → 农历必须是真实的（2026 中秋 = 农历八月十五）。"""
    from app.services import countdown_service
    m, d, text = countdown_service.solar_to_lunar(date(2026, 9, 25))
    assert (m, d) == (8, 15) and text == "八月十五"
    assert countdown_service.lunar_to_solar(8, 15, 2026) == date(2026, 9, 25)
    # 该农历月没有三十时回退到廿九，不抛异常
    assert countdown_service.lunar_to_solar(9, 30, 2026) is not None


# ---------- 账本 ----------
def test_ledger_crud_and_stats(client):
    token = register(client, "ledger_user")
    cats = client.get("/api/ledger/categories", headers=auth(token)).json()["data"]
    assert len(cats) == 9 and all(c["is_preset"] for c in cats)
    assert {"餐饮", "交通", "居住", "购物", "人情"} <= {c["name"] for c in cats}

    month = date.today().strftime("%Y-%m")
    for amount, cat, direction in ((8000, "其他", "income"),
                                   (35.5, "餐饮", "expense"), (12, "交通", "expense")):
        r = client.post("/api/ledger", headers=auth(token), json={
            "direction": direction, "amount": amount, "category": cat,
            "account": "微信", "occurred_on": date.today().isoformat(),
            "note": f"{cat}记录"}).json()
        assert r["code"] == 0, r

    # 未来日期被拒
    bad = client.post("/api/ledger", headers=auth(token), json={
        "direction": "expense", "amount": 1, "category": "餐饮",
        "occurred_on": (date.today() + timedelta(days=1)).isoformat()}).json()
    assert bad["code"] != 0

    data = client.get(f"/api/ledger?month={month}", headers=auth(token)).json()["data"]
    assert data["summary"]["expense"] == 47.5
    assert data["summary"]["income"] == 8000
    assert data["summary"]["balance"] == 7952.5
    assert len(data["items"]) == 3
    assert data["last_category"]["name"] == "交通"  # 默认选中上次使用的分类

    stats = client.get(f"/api/ledger/stats?month={month}", headers=auth(token)).json()["data"]
    assert stats["categories"][0]["name"] == "餐饮"
    assert abs(sum(c["percent"] for c in stats["categories"]) - 100) < 0.5
    assert len(stats["trend"]) == 6 and stats["trend"][-1]["month"] == month

    # 自定义分类 + 删除时账目回落「其他」
    c = client.post("/api/ledger/categories", headers=auth(token),
                    json={"name": "宠物", "emoji": "🐱"}).json()["data"]
    rec = client.post("/api/ledger", headers=auth(token), json={
        "direction": "expense", "amount": 88, "category": "宠物",
        "occurred_on": date.today().isoformat()}).json()["data"]
    assert client.delete(f"/api/ledger/categories/{c['id']}",
                         headers=auth(token)).json()["data"]["moved_to_other"] == 1
    after = client.get(f"/api/ledger?month={month}", headers=auth(token)).json()["data"]
    moved = [i for i in after["items"] if i["id"] == rec["id"]][0]
    assert moved["category"] == "其他"
    # 预置分类不可删
    r = client.delete(f"/api/ledger/categories/{cats[0]['id']}",
                      headers=auth(token)).json()["data"]
    assert r["deleted"] is False


# ---------- 足迹：旅游 + 大事件 ----------
def test_trips_and_events(client):
    token = register(client, "trip_user")
    start = date.today() - timedelta(days=5)
    r = client.post("/api/trips", headers=auth(token), json={
        "destinations": ["大理", "丽江"], "start_date": start.isoformat(),
        "end_date": date.today().isoformat(), "content": "苍山洱海",
        "cost": 3800, "companions": "老友三人"}).json()
    assert r["code"] == 0, r
    t = r["data"]
    assert t["title"] == "大理、丽江 · " + f"{start.month}月{start.day}日-{date.today().month}月{date.today().day}日"
    assert t["status"] == "ongoing"

    bad = client.post("/api/trips", headers=auth(token), json={
        "destinations": ["X"], "start_date": date.today().isoformat(),
        "end_date": (date.today() - timedelta(days=1)).isoformat()}).json()
    assert bad["code"] != 0 and "结束日期" in bad["msg"]
    no_dest = client.post("/api/trips", headers=auth(token), json={
        "destinations": [], "start_date": date.today().isoformat(),
        "end_date": date.today().isoformat()}).json()
    assert no_dest["code"] != 0

    lst = client.get("/api/trips", headers=auth(token)).json()["data"]
    assert lst["trip_count"] == 1 and lst["city_count"] == 2
    assert lst["photo_limit"] == 20

    e = client.post("/api/events", headers=auth(token), json={
        "title": "转正成功", "event_date": date.today().isoformat(),
        "category": "工作", "emoji": "💼", "mood": "🥳",
        "tags": ["工作", "里程碑"]}).json()["data"]
    assert e["tags"] == ["工作", "里程碑"] and e["is_future"] is False
    future = client.post("/api/events", headers=auth(token), json={
        "title": "明年婚礼", "event_date": (date.today() + timedelta(days=400)).isoformat(),
        "category": "家庭"}).json()["data"]
    assert future["is_future"] is True

    g = client.get("/api/events", headers=auth(token)).json()["data"]
    assert g["total"] == 2 and g["categories"][0]["name"] == "工作"


# ---------- 手札流：索引与主表一致性 ----------
def test_journal_feed_matches_records(client):
    token = register(client, "feed_user")
    client.post("/api/countdowns", headers=auth(token), json={
        "name": "妈妈生日", "date": "1965-06-01", "repeat_rule": "yearly",
        "remind_offsets": [7, 0]})
    client.post("/api/ledger", headers=auth(token), json={
        "direction": "expense", "amount": 20, "category": "餐饮",
        "occurred_on": date.today().isoformat(), "note": "午饭"})
    client.post("/api/events", headers=auth(token), json={
        "title": "第一次跑完半马", "event_date": "2025-11-03", "category": "健康"})

    home = client.get("/api/journal/home", headers=auth(token)).json()["data"]
    assert home["month_summary"]["expense"] == 20
    assert home["top_day"]["name"] == "妈妈生日"
    assert home["counts"]["ledger"] == 1 and home["counts"]["countdown"] == 1
    assert home["unread"] == 0 and home["asset_card"] is None

    # 每条索引都能点回主记录（同事务写入的核心验证）
    for item in home["feed"]["items"]:
        routes = {"ledger": "/api/ledger", "trip": "/api/trips",
                  "event": "/api/events", "countdown": "/api/countdowns"}
        if item["entry_type"] == "countdown":
            for c in client.get("/api/countdowns", headers=auth(token)).json()["data"]["items"]:
                if c["id"] == item["ref_id"]:
                    break
            else:
                raise AssertionError("索引指向的倒计时不存在")
            continue
        r = client.get(f"{routes[item['entry_type']]}/{item['ref_id']}",
                       headers=auth(token)).json()
        assert r["code"] == 0, f"{item['entry_type']} #{item['ref_id']} 404：索引与主表脱节"

    # 搜索：标题/标签命中
    s = client.get("/api/journal/search?q=半马", headers=auth(token)).json()["data"]
    assert len(s) == 1 and s[0]["entry_type"] == "event"
    s2 = client.get("/api/journal/search?q=午饭", headers=auth(token)).json()["data"]
    assert len(s2) == 1

    # 模块灰度开关接口可用
    mods = client.get("/api/journal/modules", headers=auth(token)).json()["data"]
    assert all(mods[k] for k in ("ledger", "days", "trips", "events", "assets"))

    # 索引可重建，且重建后条目数不变
    before = len(home["feed"]["items"])
    assert client.post("/api/journal/rebuild-index",
                       headers=auth(token)).json()["data"]["rebuilt"] == before
    after = client.get("/api/journal/feed", headers=auth(token)).json()["data"]
    assert len(after["items"]) == before


# ---------- 家庭资产 ----------
def test_assets_overview_and_snapshot(client):
    token = register(client, "asset_user")
    # 资产项不进手札流
    client.post("/api/assets/items", headers=auth(token), json={
        "category": "cash", "sub_category": "活期", "name": "工资卡",
        "amount": 120000, "currency": "CNY"})
    client.post("/api/assets/items", headers=auth(token), json={
        "category": "property", "sub_category": "自住", "name": "老家房子",
        "amount": 1800000, "currency": "CNY"})
    client.post("/api/assets/items", headers=auth(token), json={
        "category": "liability", "sub_category": "房贷", "name": "首套房贷",
        "amount": 900000, "currency": "CNY",
        "repay_date": (date.today() + timedelta(days=20)).isoformat()})

    # 投资持仓自动并入（不落新表）
    ensure_security("a_share", "600519", "贵州茅台")
    h = client.post("/api/holdings", headers=auth(token), json={
        "market": "a_share", "code": "600519", "name": "贵州茅台",
        "currency": "CNY", "freq": "annual"}).json()["data"]
    client.post(f"/api/holdings/{h['id']}/lots", headers=auth(token), json={
        "direction": "buy", "shares": 10, "price": 1500,
        "trade_date": "2024-01-10"})
    client.patch(f"/api/holdings/{h['id']}", headers=auth(token),
                 json={"current_price": 1600})

    ov = client.get("/api/assets", headers=auth(token)).json()["data"]
    assert ov["total_assets"] == 120000 + 1800000 + 16000
    assert ov["total_liabilities"] == 900000
    assert ov["net_worth"] == ov["total_assets"] - ov["total_liabilities"]
    assert ov["investment"]["count"] == 1
    assert [g["category"] for g in ov["groups"]] == [
        "cash", "investment", "property", "vehicle", "other", "liability"]

    pending = [g for g in ov["groups"] if g["category"] == "liability"][0]
    assert pending["items"][0]["repay_date"] is not None

    # 盘点快照
    snap = client.post("/api/assets/snapshot", headers=auth(token)).json()["data"]
    assert snap["net_worth"] == ov["net_worth"]
    trend = client.get("/api/assets/trend", headers=auth(token)).json()["data"]
    assert len(trend) == 1

    # 资产数据存在后，首页出现资产快捷卡
    home = client.get("/api/journal/home", headers=auth(token)).json()["data"]
    assert home["asset_card"] is not None
    assert home["asset_card"]["net_worth"] == ov["net_worth"]

    # 重复盘点同日只更新同一条
    client.post("/api/assets/snapshot", headers=auth(token))
    assert len(client.get("/api/assets/trend", headers=auth(token)).json()["data"]) == 1


# ---------- 提醒：幂等 ----------
def test_reminder_idempotent(client):
    token = register(client, "remind_user")
    today = date.today()
    client.post("/api/countdowns", headers=auth(token), json={
        "name": "季度考核", "date": (today + timedelta(days=7)).isoformat(),
        "repeat_rule": "once", "remind_offsets": [7, 0]})

    from app.database import engine
    from app.services import notification_service
    from sqlmodel import Session
    with Session(engine) as s:
        first = notification_service.run_daily_reminders(s, today)
        second = notification_service.run_daily_reminders(s, today)
    # 全局任务会覆盖所有用户的倒计时，这里只校验「重跑不再多发」
    assert first >= 1 and second == 0, "同一天同档位重复发送了提醒"

    data = client.get("/api/notifications", headers=auth(token)).json()["data"]
    assert data["total"] == 1 and data["unread"] == 1
    assert "准时" not in data["items"][0]["title"] + data["items"][0]["content"]
    assert "保证" not in data["items"][0]["title"] + data["items"][0]["content"]

    assert client.post("/api/notifications/read-all",
                       headers=auth(token)).json()["data"]["read"] == 1
    assert client.get("/api/notifications/unread",
                      headers=auth(token)).json()["data"]["unread"] == 0


# ---------- 软删除与回收站 ----------
def test_soft_delete_and_restore(client):
    token = register(client, "recycle_user")
    rec = client.post("/api/ledger", headers=auth(token), json={
        "direction": "expense", "amount": 66, "category": "餐饮",
        "occurred_on": date.today().isoformat(), "note": "删我试试"}).json()["data"]

    client.delete(f"/api/ledger/{rec['id']}", headers=auth(token))
    # 主表与索引都不再出现
    assert len(client.get("/api/ledger", headers=auth(token)).json()["data"]["items"]) == 0
    assert len(client.get("/api/journal/feed", headers=auth(token)).json()["data"]["items"]) == 0

    bin_ = client.get("/api/recycle-bin", headers=auth(token)).json()["data"]
    assert bin_["retain_days"] == 30 and bin_["total"] == 1
    g = bin_["groups"][0]
    assert g["label"] == "账本" and g["items"][0]["title"] == "删我试试"
    assert g["items"][0]["days_left"] == 30

    # 恢复后回到手札流
    r = client.post(f"/api/recycle-bin/ledger/{rec['id']}/restore",
                    headers=auth(token)).json()
    assert r["code"] == 0
    assert len(client.get("/api/journal/feed", headers=auth(token)).json()["data"]["items"]) == 1
    assert client.get("/api/recycle-bin", headers=auth(token)).json()["data"]["total"] == 0

    # 恢复一个不在回收站的条目 → 404
    assert client.post(f"/api/recycle-bin/ledger/{rec['id']}/restore",
                       headers=auth(token)).status_code == 404

    # 到期销毁：把删除时间改成 31 天前，purge 后照片与记录一并移除
    from app.database import engine
    from app.models import LedgerRecord
    from app.services import recycle_service
    from sqlmodel import Session
    with Session(engine) as s:
        row = s.get(LedgerRecord, rec["id"])
        row.status, row.deleted_at = "deleted", "2020-01-01 00:00:00"
        s.add(row)
        s.commit()
        assert recycle_service.purge_expired(s) == 1
        assert s.get(LedgerRecord, rec["id"]) is None


# ---------- 媒体：上传 + 归属 + 访问控制 ----------
def test_media_upload_and_isolation(client):
    token_a = register(client, "media_a")
    token_b = register(client, "media_b")

    r = client.post("/api/media/upload", headers=auth(token_a),
                    files={"file": ("receipt.png", PNG_1PX, "image/png")})
    assert r.json()["code"] == 0, r.json()
    asset = r.json()["data"]
    assert asset["mime"] == "image/png" and asset["size"] == len(PNG_1PX)

    # 本人可读
    raw = client.get(f"/api/media/{asset['id']}/raw", headers=auth(token_a))
    assert raw.status_code == 200 and raw.content == PNG_1PX
    # 他人不可读（仅本人可访问）
    assert client.get(f"/api/media/{asset['id']}/raw",
                      headers=auth(token_b)).status_code == 404
    assert client.get(f"/api/media/{asset['id']}/raw").status_code == 401

    # 未归类照片回显
    un = client.get("/api/media/unanchored", headers=auth(token_a)).json()["data"]
    assert len(un) == 1

    # 挂到一条账目上，账目删除时照片一并进回收站
    rec = client.post("/api/ledger", headers=auth(token_a), json={
        "direction": "expense", "amount": 12, "category": "餐饮",
        "occurred_on": date.today().isoformat(), "media_id": asset["id"]}).json()["data"]
    assert rec["media_id"] == asset["id"]
    assert client.get("/api/media/unanchored", headers=auth(token_a)).json()["data"] == []

    client.delete(f"/api/ledger/{rec['id']}", headers=auth(token_a))
    from app.database import engine
    from app.models import MediaAsset
    from sqlmodel import Session
    with Session(engine) as s:
        m = s.get(MediaAsset, asset["id"])
        assert m.status == "deleted" and m.owner_id == rec["id"]

    # 非法格式被拒
    bad = client.post("/api/media/upload", headers=auth(token_a),
                      files={"file": ("evil.exe", b"MZ", "application/octet-stream")})
    assert bad.json()["code"] != 0 and "仅支持" in bad.json()["msg"]


def test_media_limit_configurable(client):
    """账目照片上限走配置中心（默认 1 张），改配置后立即生效。"""
    token = register(client, "media_limit")
    from app.database import engine
    from app.services import config_service
    from sqlmodel import Session
    with Session(engine) as s:
        config_service.set_values(s, {"media_max_size_mb": "1"}, admin_id=1)
    big = b"\x89PNG\r\n\x1a\n" + b"0" * (2 * 1024 * 1024)
    r = client.post("/api/media/upload", headers=auth(token),
                    files={"file": ("big.png", big, "image/png")})
    assert r.json()["code"] != 0 and "1 MB" in r.json()["msg"]
    with Session(engine) as s:
        config_service.reset_value(s, "media_max_size_mb", admin_id=1)


# ---------- 数据导出 ----------
def test_export(client):
    token = register(client, "export_user")
    client.post("/api/ledger", headers=auth(token), json={
        "direction": "expense", "amount": 25.5, "category": "餐饮",
        "occurred_on": date.today().isoformat(), "note": "早餐"})
    js = client.get("/api/export/full", headers=auth(token))
    assert js.status_code == 200
    payload = js.json()
    assert payload["user_id"] and len(payload["ledger"]) == 1
    assert payload["index"] and payload["index"][0]["entry_type"] == "ledger"

    csv_r = client.get("/api/export/ledger.csv", headers=auth(token))
    assert csv_r.status_code == 200
    assert "早餐" in csv_r.content.decode("utf-8")
    assert csv_r.content.startswith("\ufeff".encode("utf-8"))


# ---------- 数据隔离 ----------
def test_journal_isolation(client):
    token_a = register(client, "iso_a")
    token_b = register(client, "iso_b")
    rec = client.post("/api/ledger", headers=auth(token_a), json={
        "direction": "expense", "amount": 10, "category": "餐饮",
        "occurred_on": date.today().isoformat(), "note": "只属于A"}).json()["data"]
    assert client.get("/api/ledger", headers=auth(token_b)).json()["data"]["items"] == []
    assert client.patch(f"/api/ledger/{rec['id']}", headers=auth(token_b),
                        json={"note": "改"}).status_code == 404
    assert client.delete(f"/api/ledger/{rec['id']}",
                         headers=auth(token_b)).status_code == 404
    assert client.get("/api/journal/search?q=只属于A",
                      headers=auth(token_b)).json()["data"] == []
