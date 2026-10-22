"""健康模块测试：周期预测、亲密记录、睡眠时长、隔离与注销级联。

预测口径（health_service.cycle_prediction）：
- 只有 1 条记录时用默认周期 28 天；
- 多条记录取最近 6 个有效间隔（15~60 天）的平均。
"""
from datetime import date, timedelta

from conftest import auth, register


def _d(offset: int) -> str:
    return (date.today() + timedelta(days=offset)).isoformat()


def _cycle(client, token, start, end=None, **kw):
    payload = {"start_date": start, **kw}
    if end:
        payload["end_date"] = end
    return client.post("/api/health/cycle", headers=auth(token), json=payload).json()


# ---------- 周期 ----------

def test_cycle_prediction_default_and_history(client):
    token = register(client, "health_cycle1")
    assert _cycle(client, token, _d(-28), _d(-24), flow="medium",
                  symptoms=["痛经"], note="第一天很难受")["code"] == 0
    assert _cycle(client, token, _d(0))["code"] == 0

    data = client.get("/api/health/cycle", headers=auth(token)).json()["data"]
    assert data["has_data"] is True
    assert data["cycle_len"] == 28 and data["period_len"] == 5
    assert data["last_start"] == _d(0)
    assert data["next_start"] == _d(28)
    assert data["phase"] == "period" and data["cycle_day"] == 1
    # 进行中的那条 ongoing=True，历史倒序
    assert data["ongoing"] is True
    assert data["history"][0]["start_date"] == _d(0)
    assert data["history"][1]["symptoms"] == ["痛经"]
    assert data["history"][1]["days"] == 5


def test_cycle_prediction_uses_average_interval(client):
    token = register(client, "health_cycle2")
    # 三次开始日：-60 / -32 / -4，间隔都是 28 天
    for start in (_d(-60), _d(-32), _d(-4)):
        assert _cycle(client, token, start)["code"] == 0
    data = client.get("/api/health/cycle", headers=auth(token)).json()["data"]
    assert data["cycle_len"] == 28
    assert data["next_start"] == _d(24)
    assert len(data["history"]) == 3


def test_cycle_late_and_fertile_phase(client):
    late = register(client, "health_late")
    _cycle(client, late, _d(-40))
    d = client.get("/api/health/cycle", headers=auth(late)).json()["data"]
    assert d["phase"] == "late" and d["late_days"] == 12
    assert d["days_left"] == -12

    fertile = register(client, "health_fertile")
    _cycle(client, fertile, _d(-14))
    d = client.get("/api/health/cycle", headers=auth(fertile)).json()["data"]
    assert d["phase"] == "fertile"
    assert d["ovulation"] == _d(0)


def test_cycle_validation(client):
    token = register(client, "health_cycle3")
    assert _cycle(client, token, _d(0), _d(-1))["code"] != 0          # 结束早于开始
    assert _cycle(client, token, _d(3))["code"] != 0                  # 未来日期
    assert _cycle(client, token, _d(0), flow="huge")["code"] != 0     # 流量取值非法
    assert _cycle(client, token, _d(-10))["code"] == 0
    # 同一天重复：冲突用 HTTP 409 表达，包络 code 仍是统一错误码
    assert client.post("/api/health/cycle", headers=auth(token),
                       json={"start_date": _d(-10)}).status_code == 409

    # 编辑：清空结束日 = 进行中；结束日仍不能早于开始
    rows = client.get("/api/health/cycle", headers=auth(token)).json()["data"]["history"]
    row_id = rows[0]["id"]
    r = client.patch(f"/api/health/cycle/{row_id}", headers=auth(token),
                     json={"end_date": None, "flow": "heavy"}).json()
    assert r["code"] == 0 and r["data"]["ongoing"] is True
    assert client.patch(f"/api/health/cycle/{row_id}", headers=auth(token),
                        json={"end_date": _d(-20)}).json()["code"] != 0


def test_cycle_isolation_and_delete(client):
    a = register(client, "health_cycle_a")
    b = register(client, "health_cycle_b")
    assert _cycle(client, a, _d(-5))["code"] == 0
    rid = client.get("/api/health/cycle", headers=auth(a)).json()["data"]["history"][0]["id"]

    assert client.get("/api/health/cycle", headers=auth(b)).json()["data"]["has_data"] is False
    assert client.delete(f"/api/health/cycle/{rid}", headers=auth(b)).json()["code"] != 0
    assert client.patch(f"/api/health/cycle/{rid}", headers=auth(b),
                        json={"flow": "light"}).json()["code"] != 0

    assert client.delete(f"/api/health/cycle/{rid}", headers=auth(a)).json()["code"] == 0
    assert client.get("/api/health/cycle", headers=auth(a)).json()["data"]["has_data"] is False


# ---------- 亲密 ----------

def test_intimacy_crud_and_stats(client):
    token = register(client, "health_intimacy")
    # 单人不记保护措施
    r = client.post("/api/health/intimacy", headers=auth(token), json={
        "happen_date": _d(0), "happen_time": "22:30", "kind": "self",
        "protection": "condom", "note": ""}).json()
    assert r["code"] == 0 and r["data"]["protection"] == "na"

    for kind, protection in (("partner", "condom"), ("partner", "none"), ("multi", "pill")):
        assert client.post("/api/health/intimacy", headers=auth(token), json={
            "happen_date": _d(-3), "kind": kind, "protection": protection}).json()["code"] == 0

    data = client.get("/api/health/intimacy", headers=auth(token)).json()["data"]
    assert len(data["items"]) == 4
    assert data["stats"]["month_count"] == 4
    assert data["stats"]["by_kind"] == {"self": 1, "partner": 2, "multi": 1}
    assert data["stats"]["protected_count"] == 2
    assert data["stats"]["days_since"] == 0

    # 非法类型 / 未来日期
    assert client.post("/api/health/intimacy", headers=auth(token), json={
        "happen_date": _d(0), "kind": "orgy"}).json()["code"] != 0
    assert client.post("/api/health/intimacy", headers=auth(token), json={
        "happen_date": _d(1), "kind": "partner"}).json()["code"] != 0
    # 时间格式由 schema 拦掉
    assert client.post("/api/health/intimacy", headers=auth(token), json={
        "happen_date": _d(0), "kind": "partner", "happen_time": "25:00"}).status_code == 422

    first = data["items"][0]
    r = client.patch(f"/api/health/intimacy/{first['id']}", headers=auth(token),
                     json={"kind": "multi", "note": "  纪念日  "}).json()
    assert r["code"] == 0 and r["data"]["note"] == "纪念日"
    assert client.delete(f"/api/health/intimacy/{first['id']}",
                         headers=auth(token)).json()["code"] == 0


def test_intimacy_and_sleep_pagination(client):
    """列表按 page/page_size 分页，翻页不重不漏，stats 仍按全量算。"""
    token = register(client, "health_page")
    for i in range(25):
        client.post("/api/health/intimacy", headers=auth(token), json={
            "happen_date": _d(-i), "kind": "partner"})
        client.post("/api/health/sleep", headers=auth(token), json={
            "sleep_date": _d(-i), "bed_time": "23:00", "wake_time": "07:00"})

    p1 = client.get("/api/health/intimacy?page=1&page_size=10",
                    headers=auth(token)).json()["data"]
    p2 = client.get("/api/health/intimacy?page=2&page_size=10",
                    headers=auth(token)).json()["data"]
    p3 = client.get("/api/health/intimacy?page=3&page_size=10",
                    headers=auth(token)).json()["data"]
    assert p1["total"] == 25 and p1["has_more"] is True
    assert len(p1["items"]) == 10 and len(p3["items"]) == 5
    assert p3["has_more"] is False
    ids = [i["id"] for i in p1["items"] + p2["items"] + p3["items"]]
    assert len(set(ids)) == 25
    # stats 是整表口径，不随分页缩水
    assert p1["stats"]["by_kind"]["partner"] == 25

    s2 = client.get("/api/health/sleep?page=2&page_size=10",
                    headers=auth(token)).json()["data"]
    assert s2["total"] == 25 and len(s2["items"]) == 10
    assert s2["stats"]["count"] == 25


def test_cycle_history_capped(client):
    """经期历史只回最近 24 次，避免多年记录一次全量下发。"""
    token = register(client, "health_history")
    for i in range(30):
        start = -(i * 30 + 1)
        r = _cycle(client, token, _d(start), _d(start + 3))
        assert r["code"] == 0, r
    data = client.get("/api/health/cycle", headers=auth(token)).json()["data"]
    assert len(data["history"]) == 24
    # 最近一次仍在最前
    assert data["history"][0]["start_date"] == _d(-1)


# ---------- 睡眠 ----------

def test_sleep_duration_cross_midnight(client):
    token = register(client, "health_sleep")
    r = client.post("/api/health/sleep", headers=auth(token), json={
        "sleep_date": _d(0), "bed_time": "23:30", "wake_time": "07:10", "quality": 4}).json()
    assert r["code"] == 0
    assert r["data"]["duration_min"] == 460
    assert r["data"]["hours_text"] == "7 小时 40 分"

    # 同一天重复
    assert client.post("/api/health/sleep", headers=auth(token), json={
        "sleep_date": _d(0), "bed_time": "22:00",
        "wake_time": "06:00"}).status_code == 409
    # 起睡时间相同 → 24 小时，拒绝
    assert client.post("/api/health/sleep", headers=auth(token), json={
        "sleep_date": _d(-1), "bed_time": "12:00", "wake_time": "12:00"}).json()["code"] != 0
    # 质量越界
    assert client.post("/api/health/sleep", headers=auth(token), json={
        "sleep_date": _d(-1), "bed_time": "22:00", "wake_time": "06:00",
        "quality": 6}).status_code == 422

    # 编辑时间后自动重算时长
    rid = r["data"]["id"]
    d = client.patch(f"/api/health/sleep/{rid}", headers=auth(token),
                     json={"wake_time": "06:30"}).json()["data"]
    assert d["duration_min"] == 420

    stats = client.get("/api/health/sleep", headers=auth(token)).json()["data"]["stats"]
    assert stats["avg_minutes"] == 420 and stats["avg_quality"] == 4
    assert stats["week"][0]["minutes"] == 420


def test_health_account_delete_cascade(client):
    """三张健康表都是裸外键，注销时必须一起清，否则 DELETE FROM users 会被拦住。"""
    token = register(client, "health_purge")
    _cycle(client, token, _d(-3))
    client.post("/api/health/intimacy", headers=auth(token),
                json={"happen_date": _d(-1), "kind": "partner"})
    client.post("/api/health/sleep", headers=auth(token), json={
        "sleep_date": _d(-1), "bed_time": "23:00", "wake_time": "07:00"})
    assert client.delete("/api/auth/me", headers=auth(token)).json()["code"] == 0


# ---------- 月历总览 ----------

def test_overview_marks_days(client):
    token = register(client, "health_overview")
    # 固定用「上个月」造数据，避免测试当天跨月导致断言随日期漂移
    prev_first = (date.today().replace(day=1) - timedelta(days=1)).replace(day=1)
    month = prev_first.isoformat()[:7]
    cycle_start = prev_first.replace(day=2)
    cycle_end = prev_first.replace(day=5)
    _cycle(client, token, cycle_start.isoformat(), cycle_end.isoformat(), flow="heavy")
    client.post("/api/health/intimacy", headers=auth(token), json={
        "happen_date": prev_first.replace(day=7).isoformat(),
        "kind": "partner", "protection": "condom"})
    client.post("/api/health/sleep", headers=auth(token), json={
        "sleep_date": prev_first.replace(day=8).isoformat(),
        "bed_time": "23:00", "wake_time": "07:00", "quality": 3})

    data = client.get(f"/api/health/overview?month={month}",
                      headers=auth(token)).json()["data"]
    assert data["month"] == month
    assert data["stats"]["cycle_days"] == 4
    assert data["stats"]["intimacy_count"] == 1
    assert data["stats"]["sleep_count"] == 1
    assert data["stats"]["avg_minutes"] == 480 and data["stats"]["avg_quality"] == 3

    days = {d["date"]: d for d in data["cycle_days"]}
    third = (cycle_start + timedelta(days=2)).isoformat()
    assert days[third]["day_index"] == 3
    assert days[third]["flow_label"] == "较多"
    assert days[cycle_start.isoformat()]["day_index"] == 1

    assert len(data["intimacy_days"]) == 1
    assert data["intimacy_days"][0]["date"] == prev_first.replace(day=7).isoformat()
    assert data["intimacy_days"][0]["count"] == 1
    assert data["intimacy_days"][0]["items"][0]["kind"] == "partner"

    assert data["sleep_days"][0]["date"] == prev_first.replace(day=8).isoformat()
    assert data["sleep_days"][0]["duration_min"] == 480
    assert data["sleep_days"][0]["quality"] == 3

    # 单条记录：默认 28 天周期，下次经期 = 最近一次开始 + 28
    assert data["predicted"]["period_start"] == (cycle_start + timedelta(days=28)).isoformat()
    assert data["predicted"]["period_len"] == 4
    assert data["predicted"]["period_end"] == (cycle_start + timedelta(days=31)).isoformat()


def test_overview_month_filter_and_isolation(client):
    token = register(client, "health_overview2")
    prev_first = date.today().replace(day=1) - timedelta(days=1)
    prev_first = prev_first.replace(day=1)
    start = prev_first.isoformat()
    end = (prev_first + timedelta(days=2)).isoformat()
    _cycle(client, token, start, end, flow="light")

    month = start[:7]
    data = client.get(f"/api/health/overview?month={month}",
                      headers=auth(token)).json()["data"]
    assert data["month"] == month
    assert len(data["cycle_days"]) == 3
    assert all(d["date"].startswith(month) for d in data["cycle_days"])

    # 当月没有这三类记录时是空标识，而不是报错
    this_month = date.today().isoformat()[:7]
    now = client.get(f"/api/health/overview?month={this_month}",
                     headers=auth(token)).json()["data"]
    assert now["stats"]["cycle_days"] == 0
    assert now["sleep_days"] == [] and now["intimacy_days"] == []

    # 非法月份
    assert client.get("/api/health/overview?month=2026-13",
                      headers=auth(token)).json()["code"] != 0
    # 用户隔离
    other = register(client, "health_overview3")
    other_data = client.get(f"/api/health/overview?month={month}",
                            headers=auth(other)).json()["data"]
    assert other_data["cycle_days"] == []
