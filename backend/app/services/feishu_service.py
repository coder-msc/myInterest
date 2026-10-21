"""飞书群机器人通知：把关键事件推到运营群，随时掌握应用情况。

两个硬约束：
1. 所有推送都由后端 httpx 直连飞书 —— H5 / 微信小程序 / PC 端一律不接触该链接，
   所以小程序「request 合法域名」白名单完全不受影响（那条限制只管小程序自己发的请求）。
2. 一律通过 FastAPI BackgroundTasks 调用：先返回响应，再推送。未配置、开关关闭、
   网络失败都只写日志，绝不阻塞或影响主流程。

Webhook 属于敏感凭证（拿到地址即可往群里发消息），后台脱敏展示，地址在
「系统参数 → 通知推送」里配置，默认留空。
"""
import logging

import httpx

from . import config_service
from ..utils.timeutil import now_str

log = logging.getLogger("xi.feishu")

PREFIX = "【纯牛马人生手札】"
TIMEOUT = 5.0
_MAX_TEXT = 1500


def _webhook() -> str:
    return config_service.get_text("feishu_webhook_url").strip()


def push(text: str, kind: str = "generic") -> tuple[bool, str]:
    """发一条文本消息。返回 (是否成功, 失败原因)；任何异常都不外抛。"""
    if not config_service.get_bool("feishu_notify_enabled"):
        return False, "飞书通知已在后台关闭"
    url = _webhook()
    if not url:
        log.info("feishu skipped (kind=%s): webhook 未配置", kind)
        return False, "未配置飞书 Webhook 地址"

    body = {"msg_type": "text",
            "content": {"text": text[:_MAX_TEXT]}}
    try:
        resp = httpx.post(url, json=body, timeout=TIMEOUT)
        data = resp.json() if resp.content else {}
        # 新版返回 code，老版返回 StatusCode；两者都为 0 才算成功
        code = data.get("code", data.get("StatusCode", 0))
        if resp.status_code >= 400 or code not in (0, None):
            msg = (data.get("msg") or data.get("StatusMessage")
                   or f"HTTP {resp.status_code}")
            log.warning("feishu failed (kind=%s): %s", kind, msg)
            return False, str(msg)
        log.info("feishu sent (kind=%s)", kind)
        return True, "ok"
    except Exception as exc:  # 网络/解析异常都不能影响业务
        log.warning("feishu failed (kind=%s): %s", kind, exc)
        return False, str(exc)


def _clip(text: str, limit: int) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[:limit] + "…"


# ── 各类事件 ────────────────────────────────────────────────────

def notify_verify_code(target: str, code: str, purpose: str = "login",
                       channel: str = "email") -> tuple[bool, str]:
    """验证码：开发期不用再翻服务器日志。会泄漏登录凭证，可单独关掉。"""
    if not config_service.get_bool("feishu_notify_code"):
        return False, "验证码推送已关闭"
    purpose_label = {"login": "登录/注册", "bind": "绑定邮箱"}.get(purpose, purpose)
    channel_label = {"email": "邮箱", "sms": "短信"}.get(channel, channel)
    ttl = config_service.get_int("code_ttl_minutes")
    return push(
        f"{PREFIX}🔑 验证码\n"
        f"{channel_label}：{target}\n"
        f"用途：{purpose_label}\n"
        f"验证码：{code}\n"
        f"有效期：{ttl} 分钟\n"
        f"时间：{now_str()}\n"
        f"—— 验证码等同登录凭证，请勿外传",
        kind="code")


def notify_new_user(username: str, email: str | None, nickname: str | None,
                    channel: str = "email") -> tuple[bool, str]:
    channel_label = {"email": "邮箱", "wx": "微信小程序"}.get(channel, channel)
    return push(
        f"{PREFIX}👤 新用户\n"
        f"渠道：{channel_label}\n"
        f"账号：{username}\n"
        f"邮箱：{email or '未绑定'}\n"
        f"昵称：{nickname or '-'}\n"
        f"时间：{now_str()}",
        kind="user")


def notify_account_deleted(username: str, email: str | None,
                           cleared: int = 0) -> tuple[bool, str]:
    return push(
        f"{PREFIX}🗑 账号注销\n"
        f"账号：{username}\n"
        f"邮箱：{email or '未绑定'}\n"
        f"清除记录：{cleared} 条\n"
        f"时间：{now_str()}",
        kind="account")


def notify_treehole_pending(anon_code: str, content: str,
                            created_at: str | None = None) -> tuple[bool, str]:
    return push(
        f"{PREFIX}🌳 树洞新发言待审核\n"
        f"代号：{anon_code}\n"
        f"内容：{_clip(content, 200)}\n"
        f"时间：{created_at or now_str()}\n"
        f"请到运营后台「内容运营 → 树洞审核」处理",
        kind="treehole")


def notify_feedback(username: str, content: str,
                    contact: str | None = None) -> tuple[bool, str]:
    return push(
        f"{PREFIX}💬 新用户反馈\n"
        f"用户：{username}\n"
        f"联系方式：{contact or '未留'}\n"
        f"内容：{_clip(content, 300)}\n"
        f"时间：{now_str()}",
        kind="feedback")


def notify_test() -> tuple[bool, str]:
    return push(
        f"{PREFIX}🔔 通知连通性测试\n"
        f"发送时间：{now_str()}\n"
        f"之后验证码、新用户、注销、树洞待审、用户反馈都会推到本群。",
        kind="test")
