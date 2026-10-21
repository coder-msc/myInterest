"""站内消息与提醒（PRD M9 / §7.2）。

硬规则：
- 站内消息是唯一可靠通道，所有提醒先落这里；
- 发送幂等：dedup_key 相同则跳过（同一日子的同一档位在同一天只发一条）；
- 文案不得出现「准时送达 / 保证到达」。
"""
import logging
from datetime import date, datetime, timedelta
from typing import Optional

from sqlmodel import Session, select

from ..models import Countdown, ReminderMessage, User
from ..utils.timeutil import now_str

log = logging.getLogger("xi.reminder")

KEEP_DAYS = 90  # 提醒中心只保留最近 90 天（PRD §M9）


def send(session: Session, user_id: int, title: str, content: str = "",
         kind: str = "countdown", ref_type: Optional[str] = None,
         ref_id: Optional[int] = None, dedup_key: Optional[str] = None) -> Optional[ReminderMessage]:
    """写一条站内消息；dedup_key 命中已存在则跳过（幂等）。不 commit。"""
    if dedup_key:
        hit = session.exec(select(ReminderMessage)
                           .where(ReminderMessage.user_id == user_id)
                           .where(ReminderMessage.dedup_key == dedup_key)).first()
        if hit is not None:
            return None
    msg = ReminderMessage(user_id=user_id, kind=kind, title=title, content=content,
                          ref_type=ref_type, ref_id=ref_id, dedup_key=dedup_key)
    session.add(msg)
    return msg


def out(m: ReminderMessage) -> dict:
    return {"id": m.id, "kind": m.kind, "title": m.title, "content": m.content,
            "ref_type": m.ref_type, "ref_id": m.ref_id,
            "is_read": bool(m.read_at), "read_at": m.read_at, "created_at": m.created_at}


def listing(session: Session, user_id: int, page: int = 1, page_size: int = 20) -> dict:
    stmt = select(ReminderMessage).where(ReminderMessage.user_id == user_id)
    rows = session.exec(stmt.order_by(ReminderMessage.read_at.is_not(None),
                                      ReminderMessage.created_at.desc(),
                                      ReminderMessage.id.desc())
                        .offset((page - 1) * page_size).limit(page_size)).all()
    total = len(session.exec(stmt).all())
    unread = len([r for r in session.exec(stmt).all() if not r.read_at])
    return {"items": [out(r) for r in rows], "total": total, "unread": unread,
            "page": page, "page_size": page_size, "has_more": page * page_size < total}


def unread_count(session: Session, user_id: int) -> int:
    return len(session.exec(select(ReminderMessage)
                            .where(ReminderMessage.user_id == user_id)
                            .where(ReminderMessage.read_at.is_(None))).all())


def mark_read(session: Session, user_id: int, msg_id: int) -> None:
    m = session.get(ReminderMessage, msg_id)
    if m is not None and m.user_id == user_id and not m.read_at:
        m.read_at = now_str()
        session.add(m)


def mark_all_read(session: Session, user_id: int) -> int:
    rows = session.exec(select(ReminderMessage)
                        .where(ReminderMessage.user_id == user_id)
                        .where(ReminderMessage.read_at.is_(None))).all()
    ts = now_str()
    for m in rows:
        m.read_at = ts
        session.add(m)
    return len(rows)


def delete_message(session: Session, user_id: int, msg_id: int) -> None:
    m = session.get(ReminderMessage, msg_id)
    if m is not None and m.user_id == user_id:
        session.delete(m)


def cleanup_old(session: Session) -> int:
    """提醒中心只保留最近 90 天（更早的自动清理，倒计时本身不会因此丢失）。不 commit。"""
    cutoff = (datetime.now() - timedelta(days=KEEP_DAYS)).strftime("%Y-%m-%d %H:%M:%S")
    rows = session.exec(select(ReminderMessage)
                        .where(ReminderMessage.created_at < cutoff)).all()
    for m in rows:
        session.delete(m)
    return len(rows)


def run_daily_reminders(session: Session, today: Optional[date] = None) -> int:
    """每日检查：按用户勾选档位为倒计时写站内消息（幂等）。"""
    from . import config_service, countdown_service
    if not config_service.get_bool("reminder_enabled"):
        return 0
    today = today or date.today()
    # 被禁用（封禁）的账号不发送任何提醒（PRD §7.2）
    banned = {u.id for u in session.exec(select(User).where(User.status == "banned")).all()}
    cds = session.exec(select(Countdown).where(Countdown.status == "normal")).all()
    sent = 0
    for cd in cds:
        if cd.user_id in banned:
            continue
        nxt = countdown_service.next_occurrence(cd, today)
        for offset in countdown_service.reminder_targets(cd, today):
            title, content = countdown_service.reminder_text(cd, offset, nxt)
            key = f"cd:{cd.id}:{today.isoformat()}:{offset}"
            if send(session, cd.user_id, title, content, kind="countdown",
                    ref_type="countdown", ref_id=cd.id, dedup_key=key) is not None:
                sent += 1
    if sent:
        session.commit()
        log.info("countdown reminders sent: %d", sent)
    return sent
