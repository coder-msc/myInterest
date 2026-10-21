"""回收站与数据导出（PRD §7.1 / §7.6）。

导出范围严格限定为「用户本人的全部条目」，JSON 完整字段 + 账本 CSV。
"""
import csv
import io
import json
from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlmodel import Session, select

from ..database import get_session
from ..models import (AssetItem, AssetSnapshot, Countdown, EntryIndex, LedgerRecord,
                      LifeEvent, MediaAsset, Trip, User)
from ..services import entry_service, recycle_service
from ..utils.errors import not_found, ok
from .deps import get_current_user

router = APIRouter(prefix="/api", tags=["recycle"])


@router.get("/recycle-bin")
def recycle_bin(session: Session = Depends(get_session),
                user: User = Depends(get_current_user)):
    return ok(recycle_service.listing(session, user.id))


@router.post("/recycle-bin/{entry_type}/{ref_id}/restore")
def restore(entry_type: str, ref_id: int, session: Session = Depends(get_session),
            user: User = Depends(get_current_user)):
    if not recycle_service.restore(session, user.id, entry_type, ref_id):
        raise not_found("该条目不在回收站中")
    session.commit()
    return ok({"restored": {"type": entry_type, "id": ref_id}})


@router.get("/export/full")
def export_full(session: Session = Depends(get_session),
                user: User = Depends(get_current_user)):
    """导出 JSON：完整字段（照片只给元数据与访问 id，不给存储凭证）。"""
    def rows(model, date_field=None):
        return session.exec(select(model).where(model.user_id == user.id)).all()

    def dump(o):
        return {k: v for k, v in o.__dict__.items() if not k.startswith("_")}

    payload = {
        "exported_at": date.today().isoformat(),
        "user_id": user.id,
        "ledger": [dump(r) for r in rows(LedgerRecord)],
        "trips": [dump(r) for r in rows(Trip)],
        "events": [dump(r) for r in rows(LifeEvent)],
        "countdowns": [dump(r) for r in rows(Countdown)],
        "asset_items": [dump(r) for r in rows(AssetItem)],
        "asset_snapshots": [dump(r) for r in rows(AssetSnapshot)],
        "media": [{"id": m.id, "owner_type": m.owner_type, "owner_id": m.owner_id,
                   "mime": m.mime, "size": m.size, "created_at": m.created_at}
                  for m in rows(MediaAsset) if m.status == "normal"],
        "index": [entry_service.out(r) for r in
                  session.exec(select(EntryIndex)
                               .where(EntryIndex.user_id == user.id)).all()],
    }
    body = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    return Response(content=body.encode("utf-8"), media_type="application/json; charset=utf-8",
                    headers={"Content-Disposition":
                             f'attachment; filename="journal-{date.today().isoformat()}.json"'})


@router.get("/export/ledger.csv")
def export_ledger_csv(session: Session = Depends(get_session),
                      user: User = Depends(get_current_user)):
    rows = session.exec(select(LedgerRecord)
                        .where(LedgerRecord.user_id == user.id)
                        .where(LedgerRecord.status == "normal")
                        .order_by(LedgerRecord.occurred_on)).all()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["日期", "收支", "金额", "分类", "账户", "备注"])
    for r in rows:
        writer.writerow([r.occurred_on, "支出" if r.direction == "expense" else "收入",
                         f"{r.amount:.2f}", r.category, r.account or "", r.note or ""])
    # 带 BOM，避免 Excel 打开中文乱码
    data = ("\ufeff" + buf.getvalue()).encode("utf-8")
    return Response(content=data, media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition":
                             f'attachment; filename="ledger-{date.today().isoformat()}.csv"'})
