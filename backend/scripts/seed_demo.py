"""演示数据种子脚本（可重复运行）——v0.3 纯预案模式。

造数据流程：
1. 创建/复用 demo 用户（用户名 demo，密码登录已下线，登录走邮箱验证码 demo@xi.com）
2. 17 只多市场持仓 + 多批次买入（A 股 5 + 美股 5 + 港股 3 + 基金 3 + 债券 1），
   并写入 securities.latest_price 保证市值/盈亏有数
3. 直接写 dividend_schedules（status=published），无需手动造 Dividend 记录
   —— v0.3 分红实时计算接口会自动从预案 + 持仓批次派生。

用法：
    cd backend
    python -m scripts.seed_demo            # 离线模式（不调用爬虫）
    python -m scripts.seed_demo --crawl   # 同时触发一次爬虫

幂等：重复运行前会清空 demo 用户的 holdings/lots 及相关预案，再重建。
"""
import argparse
import calendar
import json
import os
import secrets
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session, select

from app.database import engine
from app.db_init import init_db
from app.models import DividendSchedule, Holding, Lot, Security, User
from app.services.crawler_service import run_crawl
from app.services.security_service import upsert_security
from app.utils.security import hash_password

DEMO_USERNAME = "demo"
# 密码登录体系已下线：password_hash 仅存随机占位值（与 wx-login 建号一致）


def _monthly(start=(2025, 4), end=(2026, 9), rate=(2025, 0.264), rate2=(2026, 0.268)):
    """ Realty Income 月度分红：ex=月初、pay=当月 15 日，按年分档 dps。"""
    rates = {rate[0]: rate[1], rate2[0]: rate2[1]}
    rows, y, m = [], start[0], start[1]
    while (y, m) <= end:
        rows.append((f"{y}-{m:02d}-01", f"{y}-{m:02d}-01", f"{y}-{m:02d}-15",
                     rates[y], f"{y} 年 {m} 月月度分红"))
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return rows


PORTFOLIO = [
    {
        "market": "a_share", "code": "600519", "name": "贵州茅台",
        "currency": "CNY", "freq": "annual", "account": "华泰证券", "price": 1520.0,
        "lots": [
            ("2022-03-15", "buy", 60, 1580.0, 5.0),
            ("2023-09-20", "buy", 40, 1600.0, 5.0),
        ],
        "schedules": [
            ("2024-06-19", "2024-06-18", "2024-06-20", 25.91, "2023 年度分红"),
            ("2025-06-19", "2025-06-18", "2025-06-20", 30.00, "2024 年度分红"),
        ],
    },
    {
        "market": "a_share", "code": "601398", "name": "工商银行",
        "currency": "CNY", "freq": "semi_annual", "account": "华泰证券", "price": 6.90,
        "lots": [
            ("2023-03-15", "buy", 3000, 4.50, 5.0),
            ("2024-01-10", "buy", 2000, 4.80, 5.0),
        ],
        "schedules": [
            ("2024-07-16", "2024-07-15", "2024-07-17", 0.3064, "2024 中期分红"),
            ("2025-07-16", "2025-07-15", "2025-07-17", 0.3334, "2025 中期分红"),
        ],
    },
    {
        "market": "a_share", "code": "601088", "name": "中国神华",
        "currency": "CNY", "freq": "annual", "account": "中信证券", "price": 39.5,
        "lots": [
            ("2023-05-10", "buy", 2000, 28.50, 5.0),
            ("2024-02-15", "buy", 1000, 32.00, 5.0),
        ],
        "schedules": [
            ("2025-06-28", "2025-06-27", "2025-06-30", 2.55, "2024 年度分红"),
        ],
    },
    {
        "market": "a_share", "code": "600036", "name": "招商银行",
        "currency": "CNY", "freq": "semi_annual", "account": "华泰证券", "price": 48.5,
        "lots": [
            ("2022-11-20", "buy", 1000, 42.00, 5.0),
            ("2024-03-10", "buy", 500, 38.50, 5.0),
        ],
        "schedules": [
            ("2024-07-12", "2024-07-11", "2024-07-12", 1.98, "2024 中期分红"),
            ("2025-07-12", "2025-07-11", "2025-07-12", 2.10, "2025 中期分红"),
        ],
    },
    {
        "market": "a_share", "code": "600900", "name": "长江电力",
        "currency": "CNY", "freq": "annual", "account": "中信证券", "price": 28.6,
        "lots": [
            ("2023-07-18", "buy", 3000, 22.00, 5.0),
        ],
        "schedules": [
            ("2025-07-18", "2025-07-17", "2025-07-18", 0.85, "2024 年度分红"),
        ],
    },
    {
        "market": "us_stock", "code": "AAPL", "name": "Apple",
        "currency": "USD", "freq": "quarterly", "account": "富途牛牛", "price": 255.0,
        "lots": [
            ("2022-08-15", "buy", 50, 165.0, 1.0),
            ("2023-04-10", "buy", 30, 165.0, 1.0),
        ],
        "schedules": [
            ("2024-08-12", "2024-08-12", "2024-08-15", 0.25, "Q3 季度分红"),
            ("2025-05-12", "2025-05-12", "2025-05-15", 0.26, "2025 Q2 分红"),
            ("2025-08-11", "2025-08-11", "2025-08-14", 0.26, "2025 Q3 分红"),
        ],
    },
    {
        "market": "us_stock", "code": "MSFT", "name": "Microsoft",
        "currency": "USD", "freq": "quarterly", "account": "富途牛牛", "price": 505.0,
        "lots": [
            ("2023-01-20", "buy", 30, 240.0, 1.0),
            ("2024-08-01", "buy", 20, 420.0, 1.0),
        ],
        "schedules": [
            ("2024-08-15", "2024-08-15", "2024-09-10", 0.75, "Q4 季度分红"),
            ("2025-05-15", "2025-05-15", "2025-06-10", 0.83, "2025 Q2 分红"),
            ("2025-08-14", "2025-08-14", "2025-09-10", 0.83, "2025 Q3 分红"),
        ],
    },
    {
        "market": "us_stock", "code": "KO", "name": "Coca-Cola",
        "currency": "USD", "freq": "quarterly", "account": "富途牛牛", "price": 70.5,
        "lots": [
            ("2022-06-10", "buy", 200, 60.0, 1.0),
            ("2024-01-15", "buy", 100, 58.0, 1.0),
        ],
        "schedules": [
            ("2024-06-28", "2024-06-28", "2024-07-01", 0.485, "2024 Q2 分红"),
            ("2025-06-13", "2025-06-13", "2025-06-16", 0.51, "2025 Q2 分红"),
        ],
    },
    {
        "market": "us_stock", "code": "O", "name": "Realty Income",
        "currency": "USD", "freq": "monthly", "account": "长桥证券", "price": 58.6,
        "lots": [
            ("2024-09-10", "buy", 300, 57.0, 1.0),
        ],
        "schedules": _monthly(),  # 2025-04 ~ 2026-09 每月一派，月历"每月有点"效果
    },
    {
        "market": "us_stock", "code": "PG", "name": "P&G 宝洁",
        "currency": "USD", "freq": "quarterly", "account": "长桥证券", "price": 168.0,
        "lots": [
            ("2023-10-08", "buy", 60, 150.0, 1.0),
        ],
        "schedules": [
            ("2026-01-23", "2026-01-22", "2026-02-13", 1.0413, "2026 Q2 分红"),
            ("2026-04-24", "2026-04-23", "2026-05-15", 1.0568, "2026 Q3 分红"),
            ("2026-07-24", "2026-07-23", "2026-08-14", 1.0568, "2026 Q4 分红"),
        ],
    },
    {
        "market": "hk_stock", "code": "00700", "name": "腾讯控股",
        "currency": "HKD", "freq": "quarterly", "account": "富途牛牛", "price": 585.0,
        "lots": [
            ("2022-09-20", "buy", 200, 320.0, 50.0),
            ("2024-04-15", "buy", 100, 380.0, 50.0),
        ],
        "schedules": [
            ("2024-05-16", "2024-05-16", "2024-05-17", 3.40, "Q1 季度分红"),
            ("2025-05-16", "2025-05-16", "2025-05-17", 4.25, "2025 Q1 分红"),
        ],
    },
    {
        "market": "hk_stock", "code": "00005", "name": "汇丰控股",
        "currency": "HKD", "freq": "quarterly", "account": "富途牛牛", "price": 78.5,
        "lots": [
            ("2023-06-15", "buy", 400, 62.0, 50.0),
            ("2025-02-10", "buy", 200, 75.0, 50.0),
        ],
        "schedules": [
            ("2025-09-18", "2025-09-18", "2025-09-25", 0.31, "2025 第三次中期股息"),
            ("2026-03-19", "2026-03-19", "2026-03-26", 0.31, "2026 第一次中期股息"),
            ("2026-06-18", "2026-06-18", "2026-06-25", 0.31, "2026 第二次中期股息"),
        ],
    },
    {
        "market": "hk_stock", "code": "00883", "name": "中国海洋石油",
        "currency": "HKD", "freq": "semi_annual", "account": "富途牛牛", "price": 19.8,
        "lots": [
            ("2024-05-20", "buy", 2000, 17.5, 50.0),
        ],
        "schedules": [
            ("2025-09-04", "2025-09-03", "2025-09-11", 0.74, "2025 中期股息"),
            ("2026-05-27", "2026-05-26", "2026-06-25", 0.70, "2025 末期股息"),
            ("2026-09-10", "2026-09-09", "2026-09-26", 0.74, "2026 中期股息"),
        ],
    },
    {
        "market": "fund", "code": "005827", "name": "易方达蓝筹",
        "currency": "CNY", "freq": "annual", "account": "蚂蚁基金", "price": 2.85,
        "lots": [
            ("2023-02-10", "buy", 10000, 2.50, 0.0),
            ("2024-03-05", "buy", 5000, 2.20, 0.0),
        ],
        "schedules": [
            ("2024-08-20", "2024-08-20", "2024-08-21", 0.092, "2023 年度分红"),
            ("2025-08-20", "2025-08-20", "2025-08-21", 0.10, "2024 年度分红"),
        ],
    },
    {
        "market": "fund", "code": "110022", "name": "易方达消费行业",
        "currency": "CNY", "freq": "annual", "account": "蚂蚁基金", "price": 6.85,
        "lots": [
            ("2023-04-12", "buy", 5000, 5.20, 0.0),
        ],
        "schedules": [
            ("2026-01-15", "2026-01-15", "2026-01-16", 0.25, "2025 年度分红"),
        ],
    },
    {
        "market": "fund", "code": "270048", "name": "广发纯债债券C",
        "currency": "CNY", "freq": "quarterly", "account": "天天基金", "price": 1.12,
        "lots": [
            ("2024-06-18", "buy", 20000, 1.10, 0.0),
        ],
        "schedules": [
            ("2026-02-10", "2026-02-10", "2026-02-11", 0.035, "2025 四季度收益分配"),
            ("2026-05-12", "2026-05-12", "2026-05-13", 0.032, "2026 一季度收益分配"),
            ("2026-08-11", "2026-08-11", "2026-08-12", 0.033, "2026 二季度收益分配"),
        ],
    },
    {
        "market": "bond", "code": "019542", "name": "24国债12",
        "currency": "CNY", "freq": "annual", "account": "招商银行App", "price": 100.5,
        "lots": [
            ("2023-11-08", "buy", 1000, 100.2, 0.0),
        ],
        "schedules": [
            ("2026-03-20", "2026-03-19", "2026-03-21", 2.29, "2026 年度付息"),
        ],
    },
]

PENDING_SCHEDULES = [
    ("a_share", "601398", "工商银行", "2027-01-08", "2027-01-07", "2027-01-08",
     0.3800, "CNY", "crawler", 0.95, "2026 年末期分红预案"),
    ("a_share", "601088", "中国神华", "2027-06-28", "2027-06-27", "2027-06-30",
     2.80, "CNY", "crawler", 0.92, "2026 年度分红预案"),
    ("a_share", "600036", "招商银行", "2027-07-12", "2027-07-11", "2027-07-12",
     2.20, "CNY", "crawler", 0.90, "2026 中期分红预案"),
    ("a_share", "600900", "长江电力", "2027-07-18", "2027-07-17", "2027-07-18",
     0.95, "CNY", "manual", 0.60, "2026 年度分红预案（待公告）"),
    ("us_stock", "AAPL", "Apple", "2026-11-09", "2026-11-09", "2026-11-12",
     0.27, "USD", "crawler", 0.92, "2026 Q4 季度分红预案"),
    ("us_stock", "MSFT", "Microsoft", "2026-11-19", "2026-11-19", "2026-12-10",
     0.92, "USD", "crawler", 0.92, "2026 Q1 季度分红预案"),
    ("us_stock", "KO", "Coca-Cola", "2026-06-26", "2026-06-26", "2026-06-29",
     0.53, "USD", "crawler", 0.88, "2026 Q2 季度分红预案"),
    ("hk_stock", "00700", "腾讯控股", "2026-05-15", "2026-05-15", "2026-05-16",
     4.50, "HKD", "crawler", 0.90, "2026 Q1 季度分红预案"),
    ("fund", "005827", "易方达蓝筹", "2027-08-20", "2027-08-20", "2027-08-21",
     0.11, "CNY", "manual", 0.60, "2026 年度分红预案（待公告）"),
    ("hk_stock", "00883", "中国海洋石油", "2027-05-26", "2027-05-25", "2027-06-24",
     0.72, "HKD", "crawler", 0.90, "2026 末期股息预案"),
    ("us_stock", "PG", "P&G 宝洁", "2027-01-22", "2027-01-21", "2027-02-12",
     1.09, "USD", "crawler", 0.90, "2027 Q2 季度分红预案"),
    ("fund", "110022", "易方达消费行业", "2027-01-15", "2027-01-15", "2027-01-16",
     0.28, "CNY", "manual", 0.60, "2026 年度分红预案（待公告）"),
    ("bond", "019542", "24国债12", "2027-03-20", "2027-03-19", "2027-03-21",
     2.29, "CNY", "manual", 0.60, "2027 年度付息预案（待公告）"),
]


# 已发布且「即将到账」的预案（相对 2026 年 10-11 月），让 upcoming/月度统计有内容；
# 另含 2 条 2026 年内已派发的，补当年已收分红
UPCOMING_PUBLISHED = [
    # (market, code, ex_date, record_date, pay_date, dps, note)
    ("a_share", "600036", "2026-10-23", "2026-10-22", "2026-10-28", 1.20, "2026 三季度分红"),
    ("a_share", "601088", "2026-11-06", "2026-11-05", "2026-11-13", 2.26, "2026 中期分红"),
    ("hk_stock", "00700", "2026-11-13", "2026-11-12", "2026-11-20", 4.50, "2026 三季度分红"),
    ("us_stock", "KO", "2026-12-04", "2026-12-04", "2026-12-15", 0.51, "2026 Q4 分红"),
    ("a_share", "600900", "2026-07-16", "2026-07-15", "2026-07-20", 0.85, "2025 年度分红"),
    ("a_share", "601398", "2026-05-12", "2026-05-11", "2026-05-15", 0.30, "2025 年度分红"),
    ("us_stock", "O", "2026-11-02", "2026-11-02", "2026-11-13", 0.274, "2026 年 11 月月度分红"),
    ("us_stock", "O", "2026-12-01", "2026-12-01", "2026-12-15", 0.274, "2026 年 12 月月度分红"),
    ("us_stock", "PG", "2026-10-23", "2026-10-23", "2026-11-16", 1.0719, "2026 Q4 季度分红"),
    ("hk_stock", "00005", "2026-11-20", "2026-11-20", "2026-11-27", 0.31, "2026 第三次中期股息"),
    ("fund", "270048", "2026-11-10", "2026-11-10", "2026-11-11", 0.031, "2026 三季度收益分配"),
]


def get_or_create_demo_user(session: Session) -> User:
    u = session.exec(select(User).where(User.username == DEMO_USERNAME)).first()
    if u:
        return u
    u = User(username=DEMO_USERNAME, email="demo@xi.com",
             password_hash=hash_password(secrets.token_urlsafe(16)),
             nickname="演示账户", role="user")
    session.add(u)
    session.commit()
    session.refresh(u)
    print(f"  ✓ 创建 demo 用户 (id={u.id})")
    return u


def clean_demo_data(session: Session, user: User) -> None:
    """清空 demo 用户已有的 holdings/lots，以及与之匹配的预案。"""
    h_ids = [h.id for h in session.exec(select(Holding)
                                         .where(Holding.user_id == user.id)).all()]
    if h_ids:
        # 反向删：lots → holdings
        for l in session.exec(select(Lot).where(Lot.holding_id.in_(h_ids))).all():
            session.delete(l)
        session.commit()
        for h in session.exec(select(Holding).where(Holding.id.in_(h_ids))).all():
            session.delete(h)
        session.commit()
        print(f"  ✓ 清理旧数据：{len(h_ids)} 个持仓")

    # 清空 demo 相关预案（market+code 匹配 PORTFOLIO 里的标的，status 允许任何）
    for spec in PORTFOLIO:
        for sch in session.exec(select(DividendSchedule).where(
            DividendSchedule.market == spec["market"],
            DividendSchedule.code == spec["code"],
        )).all():
            session.delete(sch)
    # 清空 PENDING_SCHEDULES 里的标的（无论归属）
    for m, c, *_ in PENDING_SCHEDULES:
        for sch in session.exec(select(DividendSchedule).where(
            DividendSchedule.market == m, DividendSchedule.code == c)).all():
            session.delete(sch)
    session.commit()


def create_holding_with_lots(session: Session, user: User, spec: dict) -> Holding:
    h = Holding(user_id=user.id, market=spec["market"], code=spec["code"],
                name=spec["name"], currency=spec["currency"],
                account=spec["account"], freq=spec["freq"], note=spec.get("note", ""))
    session.add(h)
    session.flush()
    for trade_date, direction, shares, price, fee in spec["lots"]:
        session.add(Lot(user_id=user.id, holding_id=h.id,
                        trade_date=trade_date, direction=direction,
                        shares=shares, price=price, fee=fee))
    session.commit()
    session.refresh(h)
    # 确保 securities 表里有这条（爬虫没跑时也能显示 name），并写入演示现价
    sec = upsert_security(session, h.market, h.code, h.name, h.currency)
    if spec.get("price"):
        sec.latest_price = spec["price"]
        h.current_price = spec["price"]  # 持仓快照同步，避免依赖价格任务
    session.commit()
    session.refresh(h)
    return h


def create_published_schedules(session: Session, spec: dict) -> int:
    """为持仓造已发布预案（v0.3 纯预案模式，分红查询实时派生）。"""
    n = 0
    for ex_date, record_date, pay_date, dps, note in spec["schedules"]:
        # 幂等：同 (market, code, ex_date) 已存在则跳过
        exists = session.exec(select(DividendSchedule).where(
            DividendSchedule.market == spec["market"],
            DividendSchedule.code == spec["code"],
            DividendSchedule.ex_date == ex_date,
        )).first()
        if exists:
            continue
        session.add(DividendSchedule(
            market=spec["market"], code=spec["code"],
            ex_date=ex_date, record_date=record_date, pay_date=pay_date,
            dps=dps, currency=spec["currency"], div_type="cash",
            source="manual", confidence=1.0, status="published",
            raw_title=f"demo seed: {spec['name']} {note}",
        ))
        n += 1
    session.commit()
    return n


def create_upcoming_published(session: Session) -> int:
    """写入即将到账/当年已派的已发布预案（currency 按持仓本币）。"""
    n = 0
    for market, code, ex_date, rec_date, pay_date, dps, note in UPCOMING_PUBLISHED:
        exists = session.exec(select(DividendSchedule).where(
            DividendSchedule.market == market,
            DividendSchedule.code == code,
            DividendSchedule.ex_date == ex_date,
        )).first()
        if exists:
            continue
        spec = next(s for s in PORTFOLIO if s["market"] == market and s["code"] == code)
        session.add(DividendSchedule(
            market=market, code=code, name=spec["name"],
            ex_date=ex_date, record_date=rec_date, pay_date=pay_date,
            dps=dps, currency=spec["currency"], div_type="cash",
            source="manual", confidence=1.0, status="published",
            raw_title=f"demo seed: {spec['name']} {note}",
        ))
        n += 1
    session.commit()
    return n


def create_pending_schedules(session: Session) -> int:
    n = 0
    for (market, code, name, ex_date, rec_date, pay_date, dps,
         currency, source, confidence, title) in PENDING_SCHEDULES:
        exists = session.exec(select(DividendSchedule).where(
            DividendSchedule.market == market,
            DividendSchedule.code == code,
            DividendSchedule.ex_date == ex_date,
        )).first()
        if exists:
            continue
        session.add(DividendSchedule(
            market=market, code=code, name=name,
            ex_date=ex_date, record_date=rec_date, pay_date=pay_date,
            dps=dps, currency=currency, div_type="cash",
            source=source, confidence=confidence,
            status="pending", raw_title=title,
        ))
        n += 1
    session.commit()
    return n


def seed_journal(session: Session, user: User) -> None:
    """造人生手札演示数据：账本 / 足迹（旅游 + 大事件）/ 日子 / 家庭资产。

    主记录与 entry_index 索引同事务写入（PRD §4.2 硬约束），因此这里只 flush 不 commit，
    最后统一 commit —— 保证手札流里看到的每一条都能点开。
    """
    from app.models import (AssetItem, AssetSnapshot, Countdown, EntryIndex,
                            LedgerCategory, LedgerRecord, LifeEvent, Trip)
    from app.services import countdown_service, entry_service, ledger_service

    uid = user.id

    # ---------- 清空 demo 用户旧的手札数据 ----------
    for model in (EntryIndex, LedgerRecord, Trip, LifeEvent, Countdown,
                  AssetItem, AssetSnapshot):
        for row in session.exec(select(model).where(model.user_id == uid)).all():
            session.delete(row)
    for row in session.exec(select(LedgerCategory)
                            .where(LedgerCategory.user_id == uid)).all():
        session.delete(row)
    session.commit()

    ledger_service.ensure_categories(session, uid)
    ledger_service.add_category(session, uid, "工资", "💰")
    ledger_service.add_category(session, uid, "副业", "💻")

    today = date.today()

    def day_of(month_offset: int, day: int) -> str:
        idx = today.year * 12 + (today.month - 1) + month_offset
        y, m = idx // 12, idx % 12 + 1
        return date(y, m, min(day, calendar.monthrange(y, m)[1])).isoformat()

    # ---------- 账本：近 3 个月的固定支出 + 日常流水 ----------
    ledger_rows: list[tuple[str, str, float, str, str, str]] = []
    for off in (-2, -1, 0):
        ledger_rows += [
            (day_of(off, 1), "expense", 4200.0, "居住", "银行卡", "房租"),
            (day_of(off, 10), "income", 18500.0, "工资", "银行卡", "到手工资"),
            (day_of(off, 12), "expense", 320.0, "交通", "微信", "地铁通勤充值"),
            (day_of(off, 15), "expense", 186.5, "居住", "支付宝", "水电燃气"),
            (day_of(off, 18), "expense", 1299.0, "学习", "支付宝", "在线课程年费"),
        ]
    daily = [
        (-2, 2, 38.0, "餐饮", "微信", "楼下麻辣烫"),
        (-2, 4, 168.0, "购物", "支付宝", "夏季拖鞋 + 洗衣液"),
        (-2, 7, 26.0, "餐饮", "微信", "公司楼下咖啡"),
        (-2, 9, 89.0, "娱乐", "微信", "看了场电影"),
        (-2, 14, 260.0, "医疗", "支付宝", "牙科洗牙"),
        (-2, 20, 520.0, "人情", "微信", "同事结婚随礼"),
        (-2, 24, 45.5, "餐饮", "微信", "加班夜宵"),
        (-1, 2, 32.0, "餐饮", "微信", "便利店早饭"),
        (-1, 5, 420.0, "购物", "支付宝", "换了个机械键盘"),
        (-1, 8, 68.0, "餐饮", "微信", "周末小火锅"),
        (-1, 11, 1200.0, "人情", "银行卡", "给爸妈的生活费"),
        (-1, 17, 58.0, "交通", "微信", "打车去机场"),
        (-1, 23, 199.0, "娱乐", "支付宝", "演出门票"),
        (-1, 27, 38.0, "餐饮", "微信", "牛肉面"),
        (0, 1, 88.0, "餐饮", "微信", "国庆后第一顿好的"),
        (0, 3, 240.0, "购物", "支付宝", "换季外套"),
        (0, 6, 26.0, "餐饮", "微信", "豆浆油条"),
        (0, 9, 480.0, "娱乐", "支付宝", "朋友聚会 AA"),
        (0, 12, 128.0, "交通", "微信", "打车 + 停车费"),
        (0, 14, 45.0, "餐饮", "微信", "楼下小炒"),
        (0, 16, 620.0, "医疗", "支付宝", "体检套餐"),
        (0, 18, 66.0, "餐饮", "微信", "加班点的外卖"),
    ]
    for off, dd, amount, cat, acct, note in daily:
        if off == 0 and dd > today.day:
            continue
        ledger_rows.append((day_of(off, dd), "expense", amount, cat, acct, note))
    ledger_rows.append((day_of(-1, 19), "income", 3000.0, "副业", "银行卡", "接了个外包小活"))

    n_ledger = 0
    for occurred_on, direction, amount, category, account, note in sorted(ledger_rows):
        r = LedgerRecord(user_id=uid, direction=direction, amount=amount,
                         category=category, account=account, occurred_on=occurred_on,
                         note=note)
        session.add(r)
        session.flush()
        entry_service._from_ledger(session, r)
        n_ledger += 1

    # ---------- 足迹 · 旅游 ----------
    trips = [
        {"title": "成都 · 重庆 六日", "destinations": ["成都", "重庆"],
         "start_date": "2026-05-01", "end_date": "2026-05-06",
         "companions": "老婆", "cost": 6800.0,
         "content": "宽窄巷子人挤人，但火锅是真的顶。重庆轻轨穿楼那一刻，全车人都在拍。"},
        {"title": "青岛看海", "destinations": ["青岛"],
         "start_date": "2026-08-14", "end_date": "2026-08-17",
         "companions": "大学室友", "cost": 3200.0,
         "content": "八大关走了两万步，晚上在栈桥边喝到微醺。海风比空调舒服。"},
        {"title": "大理躺平四天", "destinations": ["大理"],
         "start_date": "2025-10-02", "end_date": "2025-10-05",
         "companions": "一个人", "cost": 2400.0,
         "content": "什么都不干，就是在洱海边坐着。回来之后发现，工作其实也没那么急。"},
        {"title": "日本关西（计划中）", "destinations": ["大阪", "京都", "奈良"],
         "start_date": "2026-11-08", "end_date": "2026-11-15",
         "companions": "老婆", "cost": 15000.0,
         "content": "机票酒店已订，行程待定。目标是岚山看红叶，顺便把年假用完。"},
    ]
    n_trip = 0
    for spec in trips:
        t = Trip(user_id=uid, title=spec["title"],
                 destinations=json.dumps(spec["destinations"], ensure_ascii=False),
                 start_date=spec["start_date"], end_date=spec["end_date"],
                 companions=spec["companions"], cost=spec["cost"],
                 content=spec["content"])
        session.add(t)
        session.flush()
        entry_service._from_trip(session, t)
        n_trip += 1

    # ---------- 足迹 · 大事件 ----------
    events = [
        ("第一次出国", "2024-09-10", "里程碑", "✈️", "🤩", ["第一次"],
         "护照办了三年，终于用上了。落地那一刻有点不真实。"),
        ("拿到驾照", "2025-07-01", "里程碑", "🚗", "😌", ["学车"],
         "科目二挂了两次，第三次一把过。教练说我是他带过最倔的。"),
        ("还清第一笔贷款", "2025-12-31", "财务", "💰", "🥳", ["还债"],
         "最后一笔转出去，盯着余额看了很久。无债一身轻是真的。"),
        ("跑完人生第一个半马", "2026-03-22", "健康", "🏃", "😤", ["跑步"],
         "21 公里，最后 3 公里全靠意志力。奖牌挂在了书桌前。"),
        ("搬进新家", "2026-06-18", "家庭", "🏠", "🥰", ["搬家"],
         "从看房到交房折腾了两年。第一晚睡在地板上，居然睡得很香。"),
        ("换工作满一年", "2026-09-01", "工作", "💼", "🙂", ["工作"],
         "一年过去，从手忙脚乱到能带新人。不算成功，但确实长本事了。"),
    ]
    n_event = 0
    for title, event_date, category, emoji, mood, tags, content in events:
        e = LifeEvent(user_id=uid, title=title, event_date=event_date,
                      category=category, emoji=emoji, mood=mood,
                      content=content, tags=json.dumps(tags, ensure_ascii=False))
        session.add(e)
        session.flush()
        entry_service._from_event(session, e)
        n_event += 1

    # ---------- 日子 ----------
    mom_base = "2026-11-05"
    lm, ld, lt = countdown_service.solar_to_lunar(date.fromisoformat(mom_base))
    countdowns = [
        {"name": "发薪日", "base_date": day_of(0, 10), "repeat_rule": "monthly",
         "remind_offsets": [1, 0], "pinned": 1, "emoji": "💰",
         "note": "到账后先转 30% 去定投"},
        {"name": "房租日", "base_date": day_of(0, 1), "repeat_rule": "monthly",
         "remind_offsets": [1, 0], "pinned": 0, "emoji": "🏠",
         "note": "别忘开发票"},
        {"name": "妈妈生日", "base_date": mom_base, "repeat_rule": "yearly_lunar",
         "remind_offsets": [7, 1, 0], "pinned": 1, "emoji": "🎂",
         "note": "提前订蛋糕，别只在微信说一句"},
        {"name": "结婚纪念日", "base_date": "2022-05-20", "repeat_rule": "yearly",
         "remind_offsets": [30, 7, 0], "pinned": 0, "emoji": "💍",
         "note": "第五年了，别再送同款香水"},
        {"name": "周杰伦演唱会", "base_date": "2026-11-07", "repeat_rule": "once",
         "remind_offsets": [7, 1, 0], "pinned": 0, "emoji": "🎤",
         "note": "内场票，提前两小时到"},
        {"name": "毕业纪念日", "base_date": "2018-06-30", "repeat_rule": "anniversary",
         "remind_offsets": [7, 0], "pinned": 0, "emoji": "🎓",
         "note": "老同学群里发张旧照片"},
        {"name": "和老婆在一起", "base_date": "2019-09-21", "repeat_rule": "anniversary",
         "remind_offsets": [7, 0], "pinned": 0, "emoji": "❤️",
         "note": "每年这天都吃顿好的"},
    ]
    n_cd = 0
    for spec in countdowns:
        c = Countdown(user_id=uid, name=spec["name"], base_date=spec["base_date"],
                      repeat_rule=spec["repeat_rule"],
                      remind_offsets=json.dumps(spec["remind_offsets"]),
                      pinned=spec["pinned"], emoji=spec["emoji"],
                      note=spec["note"],
                      lunar_month=lm if spec["repeat_rule"] == "yearly_lunar" else None,
                      lunar_day=ld if spec["repeat_rule"] == "yearly_lunar" else None,
                      lunar_text=lt if spec["repeat_rule"] == "yearly_lunar" else None)
        session.add(c)
        session.flush()
        entry_service._from_countdown(session, c)
        n_cd += 1

    # ---------- 家庭资产 ----------
    assets = [
        ("cash", "活期", "招商银行活期", 68000.0, "CNY", "日常开销备用"),
        ("cash", "定期", "定期存款", 120000.0, "CNY", "年化 2.1%"),
        ("cash", "活期", "美元活期", 3200.0, "USD", "之前换的，一直没动"),
        ("property", "自住", "自住房", 1850000.0, "CNY", "按最近小区成交价估"),
        ("vehicle", "代步", "家用车", 98000.0, "CNY", "开了三年"),
        ("other", "公积金", "公积金余额", 76000.0, "CNY", None),
        ("liability", "房贷", "房贷余额", 920000.0, "CNY", "还剩 18 年"),
        ("liability", "消费贷", "信用卡待还", 8600.0, "CNY", "本月账单"),
    ]
    n_asset = 0
    for category, sub, name, amount, currency, note in assets:
        a = AssetItem(user_id=uid, category=category, sub_category=sub, name=name,
                      amount=amount, currency=currency, note=note,
                      repay_date="2026-11-08" if category == "liability" else None)
        session.add(a)
        n_asset += 1

    # ---------- 资产盘点快照（趋势用） ----------
    snapshot_plan = [
        (-3, 2175000.0, 955000.0),
        (-2, 2198000.0, 948000.0),
        (-1, 2224000.0, 936000.0),
        (0, 2266000.0, 928600.0),
    ]
    n_snap = 0
    for off, total_a, total_l in snapshot_plan:
        snap_date = day_of(off, 28 if off else min(today.day, 28))
        s = AssetSnapshot(
            user_id=uid, snapshot_date=snap_date,
            total_assets=total_a, total_liabilities=total_l,
            net_worth=round(total_a - total_l, 2),
            detail=json.dumps({"cash": "现金与存款", "property": "房产",
                               "vehicle": "车辆", "other": "其他资产"},
                              ensure_ascii=False))
        session.add(s)
        session.flush()
        entry_service._from_snapshot(session, s)
        n_snap += 1

    session.commit()
    print(f"  ✓ 账本 {n_ledger} 条 · 旅游 {n_trip} 段 · 大事件 {n_event} 条 · "
          f"日子 {n_cd} 个 · 资产项 {n_asset} 项 · 盘点快照 {n_snap} 次")


def main() -> None:
    parser = argparse.ArgumentParser(description="造演示数据")
    parser.add_argument("--crawl", action="store_true",
                        help="造完数据后立即触发一次爬虫")
    parser.add_argument("--journal-only", action="store_true",
                        help="只造人生手札（账本/足迹/日子/资产）演示数据")
    args = parser.parse_args()

    os.environ.setdefault("XI_CRAWL_OFFLINE", "1")

    print("=== 息计演示数据种子脚本（v0.3 纯预案模式）===")
    init_db(seed_fx=False)
    print("✓ 数据库初始化完成（税率规则已 seed）")

    with Session(engine) as session:
        user = get_or_create_demo_user(session)
        if not args.journal_only:
            clean_demo_data(session, user)

            print(f"\n>>> 为 {user.username} 创建 {len(PORTFOLIO)} 只多市场持仓与预案...")
            total_h, total_l, total_s = 0, 0, 0
            for spec in PORTFOLIO:
                h = create_holding_with_lots(session, user, spec)
                total_h += 1
                total_l += len(spec["lots"])
                ns = create_published_schedules(session, spec)
                total_s += ns
                print(f"  ✓ {spec['market']:>9} {spec['code']:<8} {spec['name']:<12}"
                      f"  批次 {len(spec['lots'])} · 预案 {ns}")
            print(f"合计：持仓 {total_h} · 批次 {total_l} · 已发布预案 {total_s}")

            print("\n>>> 写入即将到账/当年已派的已发布预案...")
            nu = create_upcoming_published(session)
            print(f"  ✓ 新增 {nu} 条（未来到账 + 当年已派）")

            print("\n>>> 写入待确认预案（pending schedules）...")
            np = create_pending_schedules(session)
            print(f"  ✓ 新增 {np} 条 pending 预案")

        print("\n>>> 写入人生手札演示数据（账本 / 足迹 / 日子 / 家庭资产）...")
        seed_journal(session, user)

    if args.crawl:
        os.environ.pop("XI_CRAWL_OFFLINE", None)
        print("\n>>> 触发爬虫...")
        with Session(engine) as session:
            r = run_crawl(session)
            print(f"  fetched={r.get('fetched')} new_pending={r.get('new_pending')}")

    print("\n✅ 完成。用邮箱验证码登录（demo@xi.com，未配 SMTP 时验证码见后端日志），"
          "分红数据由预案 + 持仓实时派生。")


if __name__ == "__main__":
    main()
