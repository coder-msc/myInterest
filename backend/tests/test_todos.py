"""值得记 · 待办测试：快速添加、分组数据、勾选完成、排序、用户隔离、删除。

关键约束：
1. 未完成按日期升序返回（没日期的沉底），同日期的「重要」优先；
2. 勾选完成写 done_at，取消完成清空；
3. stats 按全量统计，include_done=0 只影响列表；
4. 别人的待办不可见、不可改、不可删。
"""
from datetime import date, timedelta

from conftest import auth, register


def _create(client, token, title, due=None, **kw):
    payload = {"title": title, **kw}
    if due:
        payload["due_date"] = due
    return client.post("/api/todos", headers=auth(token), json=payload).json()


def test_todo_list_and_order(client):
    token = register(client, "todo_order")
    today = date.today()
    later = (today + timedelta(days=5)).isoformat()
    tomorrow = (today + timedelta(days=1)).isoformat()

    assert _create(client, token, "没定日子的事")["code"] == 0
    assert _create(client, token, "普通的后天事", later)["code"] == 0
    assert _create(client, token, "重要的事", later, important=True)["code"] == 0
    assert _create(client, token, "明天交周报", tomorrow)["code"] == 0
    assert _create(client, token, "今天的活", today.isoformat())["code"] == 0

    data = client.get("/api/todos", headers=auth(token)).json()["data"]
    titles = [i["title"] for i in data["items"]]
    # 有日期在前按日期升序；同一天「重要」优先；没日期的最后
    assert titles == ["今天的活", "明天交周报", "重要的事", "普通的后天事", "没定日子的事"]
    assert data["stats"] == {"open": 5, "done": 0, "today": 1, "overdue": 0, "total": 5}


def test_todo_done_toggle_and_stats(client):
    token = register(client, "todo_done")
    past = (date.today() - timedelta(days=2)).isoformat()
    todo = _create(client, token, "逾期的事", past)["data"]
    assert todo["done"] is False and todo["done_at"] is None

    r = client.patch(f"/api/todos/{todo['id']}", headers=auth(token),
                     json={"done": True}).json()
    assert r["code"] == 0 and r["data"]["done"] is True and r["data"]["done_at"]

    data = client.get("/api/todos", headers=auth(token)).json()["data"]
    assert data["stats"]["open"] == 0 and data["stats"]["done"] == 1
    assert data["stats"]["overdue"] == 0

    # include_done=0：列表不含已完成，但 stats 仍统计
    data = client.get("/api/todos", headers=auth(token),
                      params={"include_done": 0}).json()["data"]
    assert data["items"] == [] and data["stats"]["done"] == 1

    # 取消完成：done_at 清空，重新回到逾期统计
    r = client.patch(f"/api/todos/{todo['id']}", headers=auth(token),
                     json={"done": False}).json()
    assert r["data"]["done"] is False and r["data"]["done_at"] is None
    data = client.get("/api/todos", headers=auth(token)).json()["data"]
    assert data["stats"]["overdue"] == 1


def test_todo_update_and_validation(client):
    token = register(client, "todo_update")
    todo = _create(client, token, "改我")["data"]

    r = client.patch(f"/api/todos/{todo['id']}", headers=auth(token), json={
        "title": "  改完的标题  ", "note": "细节", "important": True,
        "due_date": "2026-12-31"}).json()
    assert r["code"] == 0
    d = r["data"]
    assert d["title"] == "改完的标题" and d["note"] == "细节"
    assert d["important"] is True and d["due_date"] == "2026-12-31"

    # 清空日期 / 备注
    d = client.patch(f"/api/todos/{todo['id']}", headers=auth(token),
                     json={"due_date": None, "note": None}).json()["data"]
    assert d["due_date"] is None and d["note"] is None

    # 空白标题与超长标题被拦
    assert _create(client, token, "   ")["code"] != 0
    assert _create(client, token, "字" * 61)["code"] != 0
    r = client.patch(f"/api/todos/{todo['id']}", headers=auth(token),
                     json={"title": " "}).json()
    assert r["code"] != 0


def test_account_delete_cascades_todos(client):
    """注销账号必须连待办一起删：todos.user_id 是裸外键且库开了 foreign_keys=ON，
    漏删会让 DELETE FROM users 直接被外键拦住。"""
    token = register(client, "todo_purge")
    assert _create(client, token, "注销前最后一条")["code"] == 0
    assert client.delete("/api/auth/me", headers=auth(token)).json()["code"] == 0


def test_bind_email_moves_todos_to_target_account(client):
    """绑定邮箱合并账号：A 的待办要跟着迁到 B，不能因为外键拦在 DELETE FROM users 上。"""
    from app.services import verify_code_service

    a = register(client, "todo_merge_a")
    b = register(client, "todo_merge_b")
    assert _create(client, a, "A 的待办")["code"] == 0

    code = verify_code_service.generate_and_store(
        "email", "todo_merge_b@test.com", "bind")
    r = client.post("/api/auth/bind-email", headers=auth(a),
                    json={"email": "todo_merge_b@test.com", "code": code}).json()
    assert r["code"] == 0 and r["data"]["merged"] is True, r

    titles = [i["title"] for i in
              client.get("/api/todos", headers=auth(b)).json()["data"]["items"]]
    assert titles == ["A 的待办"]
    # A 的账号已不存在，旧 token 失效
    assert client.get("/api/todos", headers=auth(a)).status_code in (401, 403)


def test_todo_isolation_and_delete(client):
    alice = register(client, "todo_alice")
    bob = register(client, "todo_bob")
    todo = _create(client, alice, "alice 的私事")["data"]

    assert client.get("/api/todos", headers=auth(bob)).json()["data"]["items"] == []
    assert client.patch(f"/api/todos/{todo['id']}", headers=auth(bob),
                        json={"done": True}).json()["code"] != 0
    assert client.delete(f"/api/todos/{todo['id']}",
                         headers=auth(bob)).json()["code"] != 0

    r = client.delete(f"/api/todos/{todo['id']}", headers=auth(alice)).json()
    assert r["code"] == 0
    data = client.get("/api/todos", headers=auth(alice)).json()["data"]
    assert data["items"] == [] and data["stats"]["total"] == 0
