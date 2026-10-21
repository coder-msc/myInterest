"""树洞（发现 · 公共频道）测试：先审后发、匿名代号、每日限额、举报阈值、后台审核。

关键约束：
1. 未审核的发言不进公共列表，本人能在「我的发言」里看到状态；
2. 匿名代号固定且不含账号信息；
3. 每人每天最多 3 条；
4. 被举报 3 次自动转入 hidden，等待后台复核。
"""
from conftest import auth, register


def _make_admin(client, username):
    token = register(client, username)
    from app.database import engine
    from app.models import User
    from sqlmodel import Session, select
    with Session(engine) as s:
        u = s.exec(select(User).where(User.username == username)).first()
        u.role = "super_admin"
        s.add(u)
        s.commit()
    return token


def test_treehole_review_flow(client):
    token = register(client, "treehole_user")
    admin = _make_admin(client, "treehole_admin1")

    # 新发言默认待审，公共列表看不到
    r = client.post("/api/treehole", headers=auth(token),
                    json={"content": "今天加班到十点，饭都没吃"}).json()
    assert r["code"] == 0, r
    post = r["data"]
    assert post["status"] == "pending" and post["status_text"] == "审核中"
    assert post["anon_code"].startswith("打工人 #")

    feed = client.get("/api/treehole", headers=auth(token)).json()["data"]
    assert all(i["id"] != post["id"] for i in feed["items"])

    mine = client.get("/api/treehole/mine", headers=auth(token)).json()["data"]
    assert len(mine["items"]) == 1 and mine["items"][0]["status"] == "pending"

    # 审核通过后进入公共列表
    r = client.post(f"/api/admin/treehole/{post['id']}/approve", headers=auth(admin)).json()
    assert r["code"] == 0, r
    feed = client.get("/api/treehole", headers=auth(token)).json()["data"]
    hits = [i for i in feed["items"] if i["id"] == post["id"]]
    assert len(hits) == 1 and "status" not in hits[0]

    # 匿名代号稳定：同一个人的第二句话代号一致
    r2 = client.post("/api/treehole", headers=auth(token),
                     json={"content": "明天还要继续"}).json()["data"]
    assert r2["anon_code"] == post["anon_code"]


def test_treehole_daily_limit_and_validation(client):
    token = register(client, "treehole_limit")
    for i in range(3):
        r = client.post("/api/treehole", headers=auth(token),
                        json={"content": f"第 {i + 1} 条发言"}).json()
        assert r["code"] == 0, r
    r = client.post("/api/treehole", headers=auth(token),
                    json={"content": "第四条应该被拦"}).json()
    assert r["code"] != 0 and "今天已经发了" in r["msg"]

    q = client.get("/api/treehole/quota", headers=auth(token)).json()["data"]
    assert q["used"] == 3 and q["remaining"] == 0 and q["limit"] == 3

    # 超过 200 字被参数校验拦住
    r = client.post("/api/treehole", headers=auth(token),
                    json={"content": "字" * 201}).json()
    assert r["code"] != 0


def test_treehole_report_threshold(client):
    author = register(client, "treehole_author")
    reader = register(client, "treehole_reader")
    reporter2 = register(client, "treehole_reporter2")
    admin = _make_admin(client, "treehole_admin2")

    post = client.post("/api/treehole", headers=auth(author),
                       json={"content": "这条会被举报"}).json()["data"]
    client.post(f"/api/admin/treehole/{post['id']}/approve", headers=auth(admin))

    # 自己不能举报自己
    r = client.post(f"/api/treehole/{post['id']}/report", headers=auth(author),
                    json={"reason": "test"}).json()
    assert r["code"] != 0

    # 同一人重复举报无效
    assert client.post(f"/api/treehole/{post['id']}/report", headers=auth(reader),
                       json={"reason": "广告"}).json()["code"] == 0
    r = client.post(f"/api/treehole/{post['id']}/report", headers=auth(reader),
                    json={"reason": "广告"}).json()
    assert r["code"] != 0 and "已经举报过" in r["msg"]

    # 第二个人举报后仍未达阈值，仍可见
    client.post(f"/api/treehole/{post['id']}/report", headers=auth(reporter2),
                json={"reason": "辱骂"})
    feed = client.get("/api/treehole", headers=auth(author)).json()["data"]
    assert any(i["id"] == post["id"] for i in feed["items"])

    # 第三个人举报 → 自动 hidden，公共列表消失
    third = register(client, "treehole_reporter3")
    r = client.post(f"/api/treehole/{post['id']}/report", headers=auth(third),
                    json={"reason": "其他"}).json()
    assert r["code"] == 0 and r["data"]["reports"] == 3
    feed = client.get("/api/treehole", headers=auth(author)).json()["data"]
    assert all(i["id"] != post["id"] for i in feed["items"])

    # 后台能看到待复核记录
    hidden = client.get("/api/admin/treehole?status=hidden", headers=auth(admin)).json()["data"]
    assert hidden["total"] == 1 and hidden["items"][0]["reports"] == 3


def test_treehole_reporter_can_delete_account(client):
    """举报过别人的账号可以正常注销：举报记录带 user_id 外键，必须随账号一起删。"""
    author = register(client, "treehole_del_author")
    reporter = register(client, "treehole_del_reporter")
    admin = _make_admin(client, "treehole_admin4")

    post = client.post("/api/treehole", headers=auth(author),
                       json={"content": "举报完我就走"}).json()["data"]
    client.post(f"/api/admin/treehole/{post['id']}/approve", headers=auth(admin))
    assert client.post(f"/api/treehole/{post['id']}/report", headers=auth(reporter),
                       json={"reason": "广告"}).json()["code"] == 0

    assert client.delete("/api/auth/me", headers=auth(reporter)).json()["code"] == 0
    # 作者的匿名发言不随举报人注销而消失
    feed = client.get("/api/treehole", headers=auth(author)).json()["data"]
    assert any(i["id"] == post["id"] for i in feed["items"])


def test_treehole_reject_reason_and_delete(client):
    token = register(client, "treehole_reject")
    admin = _make_admin(client, "treehole_admin3")

    post = client.post("/api/treehole", headers=auth(token),
                       json={"content": "含有不合适内容"}).json()["data"]
    r = client.post(f"/api/admin/treehole/{post['id']}/reject", headers=auth(admin),
                    json={"reason": "含广告信息"}).json()
    assert r["code"] == 0 and r["data"]["status"] == "rejected"

    mine = client.get("/api/treehole/mine", headers=auth(token)).json()["data"]["items"]
    assert mine[0]["status"] == "rejected" and mine[0]["reason"] == "含广告信息"

    # 本人删除：状态变 deleted，不再出现在我的发言里
    assert client.delete(f"/api/treehole/{post['id']}",
                         headers=auth(token)).json()["code"] == 0
    mine = client.get("/api/treehole/mine", headers=auth(token)).json()["data"]["items"]
    assert mine == []

    # 别人删不了
    other = register(client, "treehole_other")
    post2 = client.post("/api/treehole", headers=auth(token),
                        json={"content": "另一条"}).json()["data"]
    r = client.delete(f"/api/treehole/{post2['id']}", headers=auth(other)).json()
    assert r["code"] != 0
