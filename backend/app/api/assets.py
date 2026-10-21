"""家庭资产接口（PRD M6）：净值总览、手工资产/负债、盘点快照。

调性隔离：这一层不使用玩梗文案，回到克制的专业风格。
"""
from fastapi import APIRouter, Depends
from sqlmodel import Session

from ..database import get_session
from ..models import AssetItem, User
from ..schemas import AssetItemCreate, AssetItemUpdate
from ..services import asset_service, entry_service, recycle_service
from ..utils.errors import not_found, ok
from ..utils.timeutil import now_str
from .deps import get_current_user, require_module

router = APIRouter(prefix="/api/assets", tags=["assets"],
                   dependencies=[Depends(require_module("module_assets_enabled"))])


def _owned(session: Session, user_id: int, item_id: int) -> AssetItem:
    it = session.get(AssetItem, item_id)
    if it is None or it.user_id != user_id or it.status != "normal":
        raise not_found("该项资产不存在或已删除")
    return it


@router.get("")
def overview(session: Session = Depends(get_session),
             user: User = Depends(get_current_user)):
    return ok(asset_service.overview(session, user.id))


@router.get("/trend")
def trend(session: Session = Depends(get_session),
          user: User = Depends(get_current_user)):
    return ok(asset_service.trend(session, user.id))


@router.post("/items")
def create_item(body: AssetItemCreate, session: Session = Depends(get_session),
                user: User = Depends(get_current_user)):
    it = AssetItem(user_id=user.id, category=body.category,
                   sub_category=body.sub_category, name=body.name,
                   amount=round(body.amount, 2), currency=body.currency,
                   note=body.note,
                   repay_date=body.repay_date.isoformat() if body.repay_date else None)
    session.add(it)
    session.flush()
    # 家庭资产项不进手札流（不是「人生发生的事」），但保留模块统计
    session.commit()
    session.refresh(it)
    return ok(asset_service.item_out(it))


@router.patch("/items/{item_id}")
def update_item(item_id: int, body: AssetItemUpdate, session: Session = Depends(get_session),
                user: User = Depends(get_current_user)):
    it = _owned(session, user.id, item_id)
    data = body.model_dump(exclude_unset=True)
    if "repay_date" in data:
        rd = data.pop("repay_date")
        it.repay_date = rd.isoformat() if rd else None
    for k, v in data.items():
        if v is not None:
            setattr(it, k, v)
    it.updated_at = now_str()
    session.add(it)
    session.commit()
    session.refresh(it)
    return ok(asset_service.item_out(it))


@router.delete("/items/{item_id}")
def remove_item(item_id: int, session: Session = Depends(get_session),
                user: User = Depends(get_current_user)):
    _owned(session, user.id, item_id)
    info = recycle_service.soft_delete(session, user.id, "asset_item", item_id)
    session.commit()
    return ok(info)


@router.post("/snapshot")
def take_snapshot(session: Session = Depends(get_session),
                  user: User = Depends(get_current_user)):
    """用户主动「盘点」：生成一份带日期的快照，用于趋势图。"""
    snap = asset_service.take_snapshot(session, user.id)
    entry_service._from_snapshot(session, snap)
    session.commit()
    session.refresh(snap)
    return ok(asset_service.snapshot_out(snap))
