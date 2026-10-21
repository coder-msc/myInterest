"""媒体接口（PRD §M8 / §7.3）：上传、读取、归属挂载。

照片仅本人可访问：本地存储的读取走本接口并用 token 鉴权，绝不暴露公开直链。
"""
from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import Response
from sqlmodel import Session, select

from ..database import get_session
from ..models import MediaAsset, User
from ..schemas import MediaAttachIn
from ..services import media_service
from ..services.storage import get_storage
from ..utils.errors import AppError, Codes, ok
from ..utils.timeutil import now_str
from .deps import get_current_user, get_media_user

router = APIRouter(prefix="/api/media", tags=["media"])


@router.post("/upload")
async def upload(file: UploadFile = File(...),
                 owner_type: str = Form(default="unanchored"),
                 owner_id: int | None = Form(default=None),
                 session: Session = Depends(get_session),
                 user: User = Depends(get_current_user)):
    if owner_type not in ("ledger", "trip", "event", "countdown", "unanchored"):
        owner_type = "unanchored"
    data = await file.read()
    asset = media_service.save_image(session, user.id, file.filename or "photo.jpg", data,
                                     owner_type=owner_type,
                                     owner_id=owner_id if owner_type != "unanchored" else None)
    session.commit()
    session.refresh(asset)
    return ok(media_service.asset_out(asset))


@router.get("/unanchored")
def unanchored(session: Session = Depends(get_session),
               user: User = Depends(get_current_user)):
    """未归类照片（先存照片、稍后归类）。"""
    rows = session.exec(select(MediaAsset)
                        .where(MediaAsset.user_id == user.id)
                        .where(MediaAsset.owner_type == "unanchored")
                        .where(MediaAsset.status == "normal")
                        .order_by(MediaAsset.created_at.desc())).all()
    return ok([media_service.asset_out(a) for a in rows])


@router.post("/attach")
def attach(body: MediaAttachIn, session: Session = Depends(get_session),
           user: User = Depends(get_current_user)):
    n = media_service.attach(session, user.id, body.asset_ids, body.owner_type, body.owner_id)
    session.commit()
    return ok({"attached": n})


@router.get("/{asset_id}/raw")
def raw(asset_id: int, session: Session = Depends(get_session),
        user: User = Depends(get_media_user)):
    """原件读取：支持 Bearer 头或 ?t=<token>（<image src> 无法带头，PRD §7.3 可见性）。"""
    asset = media_service.get_owned(session, user.id, asset_id)
    if asset.storage == "kodo" and asset.external_url:
        return Response(status_code=302, headers={"Location": asset.external_url})
    data = get_storage().read(asset.object_key)
    return Response(content=data, media_type=asset.mime,
                    headers={"Cache-Control": "private, max-age=86400"})


@router.delete("/{asset_id}")
def remove(asset_id: int, session: Session = Depends(get_session),
           user: User = Depends(get_current_user)):
    asset = media_service.get_owned(session, user.id, asset_id)
    if asset.status == "normal":
        asset.status, asset.deleted_at = "deleted", now_str()
        session.add(asset)
        session.commit()
    return ok({"deleted": asset_id})
