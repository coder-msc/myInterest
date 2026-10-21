"""树洞接口（发现 · 公共频道）：先审后发 + 固定匿名代号 + 每日限额。"""
from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlmodel import Session, select

from ..database import get_session
from ..models import TreeholePost, TreeholeReport, User
from ..schemas import TreeholeCreate, TreeholeReportIn
from ..services import feishu_service, treehole_service
from ..utils.errors import AppError, Codes, not_found, ok
from .deps import get_current_user, require_module

router = APIRouter(prefix="/api/treehole", tags=["treehole"],
                   dependencies=[Depends(require_module("module_treehole_enabled"))])


@router.get("")
def feed(before_id: int | None = Query(default=None),
         limit: int = Query(default=20, ge=1, le=50),
         session: Session = Depends(get_session),
         user: User = Depends(get_current_user)):
    """已审核通过的发言，按时间倒序；before_id 用于翻页。"""
    stmt = select(TreeholePost).where(TreeholePost.status == "approved")
    if before_id:
        stmt = stmt.where(TreeholePost.id < before_id)
    rows = session.exec(stmt.order_by(TreeholePost.id.desc()).limit(limit + 1)).all()  # type: ignore
    has_more = len(rows) > limit
    items = [treehole_service.out(p) for p in rows[:limit]]
    return ok({"items": items, "has_more": has_more,
               "next_before": items[-1]["id"] if has_more and items else None,
               "anon_code": treehole_service.anon_code(user.id)})


@router.get("/mine")
def my_posts(session: Session = Depends(get_session),
             user: User = Depends(get_current_user)):
    """我的发言：含审核状态与未通过原因。"""
    rows = session.exec(
        select(TreeholePost)
        .where(TreeholePost.user_id == user.id)
        .where(TreeholePost.status != "deleted")
        .order_by(TreeholePost.id.desc())  # type: ignore
        .limit(50)
    ).all()
    return ok({"items": [treehole_service.out(p, mine=True) for p in rows],
               "anon_code": treehole_service.anon_code(user.id)})


@router.get("/quota")
def my_quota(session: Session = Depends(get_session),
             user: User = Depends(get_current_user)):
    return ok(treehole_service.quota(session, user.id))


@router.post("")
def create(body: TreeholeCreate, bg: BackgroundTasks,
           session: Session = Depends(get_session),
           user: User = Depends(get_current_user)):
    post = treehole_service.create(session, user.id, body.content)
    # 推给运营群：先审后发，得有人及时去后台过审
    bg.add_task(feishu_service.notify_treehole_pending, post.anon_code,
                post.content, post.created_at)
    return ok(treehole_service.out(post, mine=True))


@router.delete("/{post_id}")
def remove(post_id: int, session: Session = Depends(get_session),
           user: User = Depends(get_current_user)):
    post = session.get(TreeholePost, post_id)
    if post is None or post.user_id != user.id or post.status == "deleted":
        raise not_found("这条发言不存在")
    post.status = "deleted"
    session.add(post)
    session.commit()
    return ok({"deleted": True})


@router.post("/{post_id}/report")
def report(post_id: int, body: TreeholeReportIn,
           session: Session = Depends(get_session),
           user: User = Depends(get_current_user)):
    """举报：达到 3 次自动转入「待复核」（隐藏），由管理员决定去留。"""
    post = session.get(TreeholePost, post_id)
    if post is None or post.status not in ("approved", "hidden"):
        raise not_found("这条发言不存在")
    if post.user_id == user.id:
        raise AppError(Codes.VALIDATION, "不能举报自己的发言")
    dup = session.exec(select(TreeholeReport)
                       .where(TreeholeReport.post_id == post_id)
                       .where(TreeholeReport.user_id == user.id)).first()
    if dup is not None:
        raise AppError(Codes.VALIDATION, "你已经举报过了")
    session.add(TreeholeReport(post_id=post_id, user_id=user.id,
                               reason=(body.reason or "").strip()[:100] or None))
    post.report_count = (post.report_count or 0) + 1
    if post.report_count >= 3 and post.status == "approved":
        post.status = "hidden"
        post.reason = "被举报达到阈值，等待复核"
    session.add(post)
    session.commit()
    return ok({"reported": True, "reports": post.report_count})
