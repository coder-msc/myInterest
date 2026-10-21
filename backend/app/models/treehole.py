"""treehole_posts 树洞发言表（发现 · 公共频道）。

先审后发：新发言默认 pending，管理员审核通过后进入 approved 才对其他人可见。
匿名代号 anon_code 由 user_id 哈希生成，固定不变但无法反推账号。
"""
from typing import Optional

from sqlmodel import Field, SQLModel

from ..utils.timeutil import now_str


class TreeholePost(SQLModel, table=True):
    __tablename__ = "treehole_posts"

    id: Optional[int] = Field(default=None, primary_key=True)
    # 不设外键：匿名频道的内容不随账号删除而消失，也便于演示数据造假名代号
    user_id: int = Field(index=True)
    anon_code: str = Field(default="", index=True)        # 固定匿名代号，如「打工人 #7F2A」
    content: str = Field(default="")                      # 纯文字（≤200 字）
    status: str = Field(default="pending", index=True)    # pending/approved/rejected/hidden/deleted
    reason: Optional[str] = None                          # 拒绝或下架原因
    report_count: int = Field(default=0)                  # 被举报次数
    reviewed_by: Optional[int] = None                     # 审核人 user_id
    reviewed_at: Optional[str] = None
    created_at: str = Field(default_factory=now_str, index=True)


class TreeholeReport(SQLModel, table=True):
    __tablename__ = "treehole_reports"

    id: Optional[int] = Field(default=None, primary_key=True)
    post_id: int = Field(foreign_key="treehole_posts.id", index=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    reason: Optional[str] = None
    created_at: str = Field(default_factory=now_str, index=True)
