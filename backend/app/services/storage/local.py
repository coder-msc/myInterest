"""本地磁盘存储实现：文件落在 backend/data/media/ 下。

仅用于开发与 H5 联调：本地文件没有公开外链，必须经由带身份校验的
/api/media/{id}/raw 读取。微信小程序要求 HTTPS 域名，上线前需切七牛。
"""
from pathlib import Path

from ...config import DATA_DIR


class LocalStorage:
    name = "local"

    def __init__(self) -> None:
        self.root = Path(DATA_DIR) / "media"
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        # key 由服务层生成（u{uid}/{yyyymm}/{uuid}.ext），这里再做一次越界防护
        p = (self.root / key).resolve()
        if not str(p).startswith(str(self.root.resolve())):
            raise ValueError("非法对象键")
        return p

    def save(self, data: bytes, key: str, mime: str = "image/jpeg") -> str | None:
        p = self._path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return None  # 无外链：读取走鉴权接口

    def read(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def delete(self, key: str) -> None:
        try:
            self._path(key).unlink()
        except FileNotFoundError:
            pass
