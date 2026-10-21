"""七牛云 Kodo 存储实现（PRD §M8）。

不引入七牛 SDK：上传凭证用 HMAC-SHA1 自签（与官方算法一致），
上传走 up.qiniup.com 的表单接口，删除走 rs.qiniup.com 的管理接口，
HTTP 客户端复用项目已有的 httpx，保持依赖面最小。

四项配置（config_service「媒体存储」分组）齐全才可用，缺一即报错并提示去后台配置。
"""
import base64
import hashlib
import hmac
import json
import time

import httpx

from ...utils.errors import AppError, Codes

_UPLOAD_HOST_DEFAULT = "https://upload.qiniup.com"
_MANAGE_HOST = "https://rs.qiniup.com"


def _urlsafe_b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


class KodoStorage:
    name = "kodo"

    def __init__(self) -> None:
        # 每次操作都实时读配置（config_service 自带 60s 缓存），
        # 便于管理员在后台改完 AK/域名后不用重启进程
        self._cfg = None

    def _config(self) -> dict:
        from .. import config_service
        ak = config_service.get_text("qiniu_access_key").strip()
        sk = config_service.get_text("qiniu_secret_key").strip()
        bucket = config_service.get_text("qiniu_bucket").strip()
        domain = config_service.get_text("qiniu_domain").strip().rstrip("/")
        if not (ak and sk and bucket and domain):
            raise AppError(Codes.VALIDATION,
                           "七牛云存储未配置完整：请在后台「配置管理 → 媒体存储」补齐 "
                           "AccessKey / SecretKey / Bucket / 绑定域名，或把存储方式改回 local。",
                           status=400)
        if not domain.startswith("http"):
            domain = "https://" + domain
        return {"ak": ak, "sk": sk, "bucket": bucket, "domain": domain}

    # ── 凭证 ────────────────────────────────────────────────
    def _upload_token(self, key: str, expires: int = 3600) -> str:
        cfg = self._config()
        policy = {"scope": f"{cfg['bucket']}:{key}", "deadline": int(time.time()) + expires}
        encoded = _urlsafe_b64(json.dumps(policy, separators=(",", ":")).encode())
        sign = hmac.new(cfg["sk"].encode(), encoded.encode(), hashlib.sha1).digest()
        return f"{cfg['ak']}:{_urlsafe_b64(sign)}:{encoded}"

    def _manage_token(self, path: str, body: str = "") -> str:
        cfg = self._config()
        data = f"{path}\n{body}".encode()
        sign = hmac.new(cfg["sk"].encode(), data, hashlib.sha1).digest()
        return f"QBox {cfg['ak']}:{_urlsafe_b64(sign)}"

    # ── 接口 ────────────────────────────────────────────────
    def save(self, data: bytes, key: str, mime: str = "image/jpeg") -> str | None:
        cfg = self._config()
        token = self._upload_token(key)
        files = {"file": (key.split("/")[-1], data, mime)}
        resp = httpx.post(_UPLOAD_HOST_DEFAULT,
                          data={"token": token, "key": key},
                          files=files, timeout=60)
        if resp.status_code != 200:
            raise AppError(Codes.SERVER_ERROR,
                           f"七牛上传失败：{resp.text[:200]}", status=502)
        return f"{cfg['domain']}/{key}"

    def read(self, key: str) -> bytes:
        """七牛上的图片通过外链直读（服务端仅在看不动时兜底）。"""
        cfg = self._config()
        resp = httpx.get(f"{cfg['domain']}/{key}", timeout=60)
        resp.raise_for_status()
        return resp.content

    def delete(self, key: str) -> None:
        cfg = self._config()
        entry = _urlsafe_b64(f"{cfg['bucket']}:{key}".encode())
        path = f"/delete/{entry}"
        resp = httpx.post(_MANAGE_HOST + path, headers={"Authorization": self._manage_token(path)},
                          timeout=30)
        # 614 = 目标不存在（重复删除），视为成功
        if resp.status_code not in (200, 612, 614):
            raise AppError(Codes.SERVER_ERROR, f"七牛删除失败：{resp.text[:200]}", status=502)

    # 缩略图：七牛 imageView2 URL 参数，不自建图片服务（PRD §M8）
    @staticmethod
    def thumb_url(url: str | None, width: int = 400) -> str | None:
        if not url:
            return None
        sep = "&" if "?" in url else "?"
        return f"{url}{sep}imageView2/2/w/{width}/format/webp"
