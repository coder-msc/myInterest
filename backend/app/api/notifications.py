"""提醒中心接口（PRD M9）：站内消息列表、已读、删除。

产品红线：所有文案不得承诺「准时送达 / 保证到达」；站内消息是唯一可靠通道。
"""
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from ..database import get_session
from ..models import User
from ..services import notification_service
from ..utils.errors import ok
from .deps import get_current_user

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("")
def listing(page: int = Query(default=1, ge=1),
            page_size: int = Query(default=20, ge=1, le=50),
            session: Session = Depends(get_session),
            user: User = Depends(get_current_user)):
    return ok(notification_service.listing(session, user.id, page, page_size))


@router.get("/unread")
def unread(session: Session = Depends(get_session),
           user: User = Depends(get_current_user)):
    return ok({"unread": notification_service.unread_count(session, user.id)})


@router.post("/{msg_id}/read")
def mark_read(msg_id: int, session: Session = Depends(get_session),
              user: User = Depends(get_current_user)):
    notification_service.mark_read(session, user.id, msg_id)
    session.commit()
    return ok({"read": msg_id})


@router.post("/read-all")
def mark_all_read(session: Session = Depends(get_session),
                  user: User = Depends(get_current_user)):
    n = notification_service.mark_all_read(session, user.id)
    session.commit()
    return ok({"read": n})


@router.delete("/{msg_id}")
def remove(msg_id: int, session: Session = Depends(get_session),
           user: User = Depends(get_current_user)):
    notification_service.delete_message(session, user.id, msg_id)
    session.commit()
    return ok({"deleted": msg_id})
