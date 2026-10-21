"""media_assets 媒体资产表：照片上传记录（PRD §7.3 / M8）。

存储走可切换抽象（services/storage/）：
- storage='local'：文件落在 backend/data/media/ 下，访问需带身份校验（/api/media/{id}/raw）
- storage='kodo' ：七牛云 Kodo，external_url 为绑定域名下的完整 HTTPS 外链

owner_type/owner_id 表达归属：账目用 media_id 单图引用；行程/大事件用
owner_type+owner_id 挂多图（sort_order 排序）；owner_type='unanchored' 表示
「先存照片、稍后归类」的未归类照片。
"""
from typing import Optional

from sqlmodel import Field, SQLModel

from ..utils.timeutil import now_str


class MediaAsset(SQLModel, table=True):
    __tablename__ = "media_assets"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)  # 归属用户（仅本人可访问）
    owner_type: Optional[str] = Field(default=None, index=True)  # ledger/trip/event/countdown/unanchored
    owner_id: Optional[int] = Field(default=None, index=True)    # 归属主表记录 id
    storage: str = Field(default="local")   # local / kodo
    object_key: str                          # 对象键（本地为相对文件名，七牛为 key）
    external_url: Optional[str] = None       # 外链地址（七牛绑定域名）；本地为空，走鉴权接口
    thumb_url: Optional[str] = None          # 缩略图地址（七牛 imageView2 参数；本地同原图）
    mime: str = Field(default="image/jpeg")
    ext: str = Field(default="jpg")
    size: int = Field(default=0)             # 字节数
    width: Optional[int] = None
    height: Optional[int] = None
    sort_order: int = Field(default=0)       # 多图时的展示顺序
    status: str = Field(default="normal", index=True)  # normal / deleted / purged
    deleted_at: Optional[str] = None
    created_at: str = Field(default_factory=now_str)
    updated_at: str = Field(default_factory=now_str)
