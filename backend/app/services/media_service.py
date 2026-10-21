"""媒体服务：上传校验、落盘/上云、归属挂载、软删除联动（PRD §7.3 / M8）。

可见性硬规则：只有本人可访问；本地存储走 /api/media/{id}/raw（带 token 鉴权），
七牛存储走绑定域名的外链。管理员后台不提供照片原件预览（PRD §7.4 红线）。
"""
import json
import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import Session, select

from ..models import MediaAsset
from ..utils.errors import AppError, Codes
from ..utils.timeutil import now_str
from .storage import get_storage
from .storage.kodo import KodoStorage

# 可接受格式（PRD §7.3）；heic 在浏览器无法直接渲染，但允许上传留存原图
EXT_MIME = {
    "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
    "webp": "image/webp", "heic": "image/heic", "heif": "image/heic",
}
MAX_NAME_LEN = 8


def norm_ext(filename: str) -> str:
    ext = (filename or "").rsplit(".", 1)[-1].lower() if "." in (filename or "") else ""
    if ext not in EXT_MIME:
        raise AppError(Codes.VALIDATION,
                       "仅支持 jpg / jpeg / png / webp / heic 格式的图片", status=422)
    return ext


def asset_url(asset: MediaAsset) -> str:
    """对外访问地址：七牛返回外链；本地返回带鉴权的读取接口路径。"""
    if asset.external_url:
        return asset.external_url
    return f"/api/media/{asset.id}/raw"


def asset_out(asset: MediaAsset, with_thumb: bool = True) -> dict:
    url = asset_url(asset)
    thumb = asset.thumb_url
    if with_thumb and not thumb and asset.storage == "kodo":
        thumb = KodoStorage.thumb_url(asset.external_url)
    return {
        "id": asset.id, "owner_type": asset.owner_type, "owner_id": asset.owner_id,
        "url": url, "thumb_url": thumb or url,
        "mime": asset.mime, "size": asset.size, "sort_order": asset.sort_order,
        "created_at": asset.created_at,
    }


def save_image(session: Session, user_id: int, filename: str, data: bytes,
               owner_type: Optional[str] = None, owner_id: Optional[int] = None,
               sort_order: int = 0) -> MediaAsset:
    """校验并保存一张图片（调用方负责 commit，保证与主记录同一事务）。"""
    from . import config_service
    ext = norm_ext(filename)
    max_mb = config_service.get_int("media_max_size_mb")
    if len(data) > max_mb * 1024 * 1024:
        raise AppError(Codes.VALIDATION,
                       f"单张图片不能超过 {max_mb} MB（当前 {len(data) / 1048576:.1f} MB）",
                       status=422)
    if not data:
        raise AppError(Codes.VALIDATION, "上传文件为空", status=422)

    storage = get_storage()
    key = f"u{user_id}/{datetime.now().strftime('%Y%m')}/{uuid.uuid4().hex}.{ext}"
    external_url = storage.save(data, key, EXT_MIME[ext])
    asset = MediaAsset(user_id=user_id, owner_type=owner_type, owner_id=owner_id,
                       storage=storage.name, object_key=key, external_url=external_url,
                       mime=EXT_MIME[ext], ext=ext, size=len(data), sort_order=sort_order)
    session.add(asset)
    session.flush()  # 拿到 id，便于调用方把它写进主表
    return asset


def get_owned(session: Session, user_id: int, asset_id: int) -> MediaAsset:
    a = session.get(MediaAsset, asset_id)
    if a is None or a.user_id != user_id:
        raise AppError(Codes.NOT_FOUND, "图片不存在或不属于当前用户", status=404)
    return a


def list_by_ids(session: Session, user_id: int, ids: list[int]) -> list[MediaAsset]:
    if not ids:
        return []
    rows = session.exec(select(MediaAsset)
                        .where(MediaAsset.user_id == user_id)
                        .where(MediaAsset.id.in_(ids))).all()
    order = {aid: i for i, aid in enumerate(ids)}
    return sorted(rows, key=lambda a: order.get(a.id, 0))


def list_for_owner(session: Session, user_id: int,
                   owner_type: str, owner_id: int) -> list[MediaAsset]:
    return session.exec(select(MediaAsset)
                        .where(MediaAsset.user_id == user_id)
                        .where(MediaAsset.owner_type == owner_type)
                        .where(MediaAsset.owner_id == owner_id)
                        .where(MediaAsset.status == "normal")
                        .order_by(MediaAsset.sort_order)).all()


def count_for_owner(session: Session, user_id: int, owner_type: str, owner_id: int) -> int:
    return len(list_for_owner(session, user_id, owner_type, owner_id))


def attach(session: Session, user_id: int, asset_ids: list[int],
           owner_type: str, owner_id: int, start_order: int = 0) -> int:
    """把「未归类照片」挂到某条主记录上（M8 先存照片、稍后归类）。"""
    n = 0
    for i, aid in enumerate(asset_ids):
        a = session.get(MediaAsset, aid)
        if a is None or a.user_id != user_id or a.status != "normal":
            continue
        if a.owner_type not in (None, "unanchored") and a.owner_id not in (None, owner_id):
            continue  # 已被别的条目占用，跳过
        a.owner_type, a.owner_id = owner_type, owner_id
        a.sort_order = start_order + i
        a.updated_at = now_str()
        session.add(a)
        n += 1
    return n


def replace_owner_media(session: Session, user_id: int, owner_type: str, owner_id: int,
                        asset_ids: list[int]) -> None:
    """按提交的 id 列表重排/解绑：不在列表中的旧图转入未归类（不直接删除）。"""
    keep = set(asset_ids)
    for a in session.exec(select(MediaAsset)
                          .where(MediaAsset.user_id == user_id)
                          .where(MediaAsset.owner_type == owner_type)
                          .where(MediaAsset.owner_id == owner_id)).all():
        if a.id not in keep:
            a.owner_type, a.owner_id = "unanchored", None
            session.add(a)
    for i, aid in enumerate(asset_ids):
        a = session.get(MediaAsset, aid)
        if a is None or a.user_id != user_id:
            continue
        a.owner_type, a.owner_id, a.sort_order = owner_type, owner_id, i
        session.add(a)


def soft_delete_owner(session: Session, user_id: int, owner_type: str, owner_id: int) -> int:
    """条目删除时照片一并进入回收站（不删文件，等销毁时才真删）。"""
    n = 0
    for a in session.exec(select(MediaAsset)
                          .where(MediaAsset.user_id == user_id)
                          .where(MediaAsset.owner_type == owner_type)
                          .where(MediaAsset.owner_id == owner_id)
                          .where(MediaAsset.status == "normal")).all():
        a.status, a.deleted_at = "deleted", now_str()
        session.add(a)
        n += 1
    return n


def restore_owner(session: Session, user_id: int, owner_type: str, owner_id: int) -> int:
    n = 0
    for a in session.exec(select(MediaAsset)
                          .where(MediaAsset.user_id == user_id)
                          .where(MediaAsset.owner_type == owner_type)
                          .where(MediaAsset.owner_id == owner_id)
                          .where(MediaAsset.status == "deleted")).all():
        a.status, a.deleted_at = "normal", None
        session.add(a)
        n += 1
    return n


def purge_asset(session: Session, asset: MediaAsset) -> None:
    """真删文件（回收站到期销毁时调用）。"""
    try:
        get_storage().delete(asset.object_key)
    except Exception:  # 存储侧删失败不阻断条目销毁
        pass
    asset.status = "purged"
    session.add(asset)


def stats(session: Session) -> dict:
    """后台看板用：照片总数与占用空间（不含原件内容，PRD §7.4 红线）。"""
    rows = session.exec(select(MediaAsset).where(MediaAsset.status == "normal")).all()
    return {"photos": len(rows), "bytes": sum(r.size for r in rows)}


def parse_ids(raw: Optional[str]) -> list[int]:
    """请求里照片 id 列表可能是 JSON 数组字符串，统一解析。"""
    if not raw:
        return []
    try:
        v = json.loads(raw)
    except Exception:
        return []
    return [int(x) for x in v if str(x).isdigit()] if isinstance(v, list) else []
