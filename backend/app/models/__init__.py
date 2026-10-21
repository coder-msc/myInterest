"""汇总导出全部表模型，保证 create_all 能建齐所有表。"""
from .admin_operation_log import AdminOperationLog
from .announcement import Announcement
from .asset import AssetItem, AssetSnapshot
from .countdown import Countdown
from .dividend_schedule import DividendSchedule
from .entry_index import EntryIndex
from .exchange_rate import ExchangeRate
from .feedback import Feedback
from .holding import Holding
from .ledger import LedgerCategory, LedgerRecord
from .life_event import LifeEvent
from .lot import Lot
from .media_asset import MediaAsset
from .reminder_message import ReminderMessage
from .security import Security
from .system_config import SystemConfig
from .tax_rule import TaxRule
from .todo import Todo
from .treehole import TreeholePost, TreeholeReport
from .trip import Trip
from .user import User
from .user_setting import UserSetting
from .verify_code import VerifyCode

__all__ = [
    "User",
    "Holding",
    "Lot",
    "SystemConfig",
    "DividendSchedule",
    "Security",
    "ExchangeRate",
    "TaxRule",
    "UserSetting",
    "Announcement",
    "Feedback",
    "AdminOperationLog",
    "VerifyCode",
    # 人生手札
    "EntryIndex",
    "MediaAsset",
    "LedgerRecord",
    "LedgerCategory",
    "Trip",
    "LifeEvent",
    "Countdown",
    "ReminderMessage",
    "AssetItem",
    "AssetSnapshot",
    "TreeholePost",
    "TreeholeReport",
    "Todo",
]
