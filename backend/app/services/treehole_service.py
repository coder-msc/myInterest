"""树洞服务（发现 · 公共频道）：匿名代号、发言限额、审核流转。"""
import hashlib
from datetime import date

from sqlmodel import Session, select

from ..models import TreeholePost
from ..utils.errors import AppError, Codes
from ..utils.timeutil import now_str

DAILY_LIMIT = 3          # 每人每天最多发 3 条
CONTENT_MAX = 200        # 纯文字，最多 200 字
CONTENT_MIN = 2

STATUS_TEXT = {
    "pending": "审核中",
    "approved": "已通过",
    "rejected": "未通过",
    "hidden": "已下架",
    "deleted": "已删除",
}


def anon_code(user_id: int) -> str:
    """固定匿名代号：同一个人永远是同一个代号，但无法反推账号。"""
    digest = hashlib.sha256(f"treehole-{user_id}".encode()).hexdigest()[:4].upper()
    return f"打工人 #{digest}"


def clean(content: str) -> str:
    text = (content or "").strip()
    if len(text) < CONTENT_MIN:
        raise AppError(Codes.VALIDATION, "说点什么吧，至少 2 个字")
    if len(text) > CONTENT_MAX:
        raise AppError(Codes.VALIDATION, f"最多 {CONTENT_MAX} 字，删一点再说")
    return text


def out(p: TreeholePost, mine: bool = False) -> dict:
    data = {
        "id": p.id,
        "anon_code": p.anon_code,
        "content": p.content,
        "reports": p.report_count,
        "created_at": p.created_at,
    }
    if mine:
        data["status"] = p.status
        data["status_text"] = STATUS_TEXT.get(p.status, p.status)
        data["reason"] = p.reason
        data["reviewed_at"] = p.reviewed_at
    return data


def daily_used(session: Session, user_id: int) -> int:
    """今天已经发了几条（删除的不占额度）。"""
    today = date.today().isoformat()
    rows = session.exec(
        select(TreeholePost)
        .where(TreeholePost.user_id == user_id)
        .where(TreeholePost.status != "deleted")
        .where(TreeholePost.created_at.startswith(today))
    ).all()
    return len(rows)


def quota(session: Session, user_id: int) -> dict:
    used = daily_used(session, user_id)
    return {"used": used, "limit": DAILY_LIMIT,
            "remaining": max(0, DAILY_LIMIT - used), "max_length": CONTENT_MAX}


def create(session: Session, user_id: int, content: str) -> TreeholePost:
    text = clean(content)
    if daily_used(session, user_id) >= DAILY_LIMIT:
        raise AppError(Codes.VALIDATION, f"今天已经发了 {DAILY_LIMIT} 条，明天再来")
    post = TreeholePost(user_id=user_id, anon_code=anon_code(user_id),
                        content=text, status="pending")
    session.add(post)
    session.commit()
    session.refresh(post)
    return post


def review(session: Session, post: TreeholePost, admin_id: int,
           status: str, reason: str | None = None) -> TreeholePost:
    """审核流转：approved / rejected / hidden。"""
    post.status = status
    post.reason = reason
    post.reviewed_by = admin_id
    post.reviewed_at = now_str()
    session.add(post)
    session.commit()
    session.refresh(post)
    return post
