"""飞书通知测试：不联网，全部 monkeypatch httpx.post。

覆盖：
1. 未配置 / 总开关关闭 / 验证码子开关关闭 → 一个请求都不发；
2. 正常推送：payload 是飞书要求的 msg_type=text，验证码原文出现在消息里；
3. 飞书返回业务错误码、网络异常 → 返回 False 且不抛异常（绝不能影响主流程）；
4. send-code 接口挂上 BackgroundTasks 后仍返回 code=0（未配置时后台任务静默跳过）。
"""
import httpx

from app.services import config_service, feishu_service
from conftest import auth, register


class _Resp:
    def __init__(self, data, status_code=200):
        self._data = data
        self.status_code = status_code
        self.content = b"{}"

    def json(self):
        return self._data


def _setup(monkeypatch, **overrides):
    values = {
        "feishu_webhook_url": "https://open.feishu.cn/open-apis/bot/v2/hook/test",
        "feishu_notify_enabled": "1",
        "feishu_notify_code": "1",
        "code_ttl_minutes": "10",
    }
    values.update(overrides)
    monkeypatch.setattr(config_service, "get_text", lambda key: values.get(key, ""))
    sent = []

    def fake_post(url, json=None, timeout=None):
        sent.append({"url": url, "json": json})
        return _Resp({"code": 0, "msg": "success"})

    monkeypatch.setattr(httpx, "post", fake_post)
    return sent


def test_skip_when_webhook_missing(monkeypatch):
    sent = _setup(monkeypatch, feishu_webhook_url="")
    ok_, msg = feishu_service.notify_verify_code("a@b.com", "123456", "login", "email")
    assert ok_ is False and "Webhook" in msg
    assert sent == []


def test_skip_when_master_switch_off(monkeypatch):
    sent = _setup(monkeypatch, feishu_notify_enabled="0")
    ok_, msg = feishu_service.push("hello")
    assert ok_ is False and "关闭" in msg
    assert sent == []


def test_skip_code_when_code_switch_off(monkeypatch):
    sent = _setup(monkeypatch, feishu_notify_code="0")
    ok_, _ = feishu_service.notify_verify_code("a@b.com", "123456")
    assert ok_ is False
    assert sent == []
    # 其他通知不受验证码子开关影响
    ok_, _ = feishu_service.notify_new_user("alice", "a@b.com", "Alice", "email")
    assert ok_ is True and len(sent) == 1


def test_verify_code_payload(monkeypatch):
    sent = _setup(monkeypatch)
    ok_, _ = feishu_service.notify_verify_code("demo@xi.com", "806308", "bind", "email")
    assert ok_ is True and len(sent) == 1
    payload = sent[0]["json"]
    assert payload["msg_type"] == "text"
    text = payload["content"]["text"]
    assert "806308" in text and "demo@xi.com" in text
    assert "绑定邮箱" in text and "10 分钟" in text


def test_business_error_does_not_raise(monkeypatch):
    _setup(monkeypatch)
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _Resp(
        {"code": 19021, "msg": "sign match fail"}, status_code=200))
    ok_, msg = feishu_service.push("x")
    assert ok_ is False and "sign match fail" in msg


def test_network_error_does_not_raise(monkeypatch):
    _setup(monkeypatch)

    def boom(*a, **k):
        raise httpx.ConnectError("network down")

    monkeypatch.setattr(httpx, "post", boom)
    ok_, msg = feishu_service.push("x")
    assert ok_ is False and "network down" in msg


def test_send_code_endpoint_still_ok(client, monkeypatch):
    """未配置 webhook 时，后台任务应静默跳过，接口照常返回。"""
    real_get_text = config_service.get_text
    # 只清空飞书相关配置，其余（限流阈值等）保持真实默认值
    monkeypatch.setattr(config_service, "get_text",
                        lambda key: "" if key.startswith("feishu_") else real_get_text(key))
    r = client.post("/api/auth/send-code",
                    json={"channel": "email", "target": "feishu@test.com",
                          "purpose": "login"}).json()
    assert r["code"] == 0 and r["data"]["sent"] is True
