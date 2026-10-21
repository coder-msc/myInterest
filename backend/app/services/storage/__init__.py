"""媒体存储抽象（PRD §7.3）：按配置 media_provider 选择具体实现。

业务侧只依赖 services.media_service，切换存储只需改配置中心
「媒体存储 → 存储方式」（local / kodo），不改任何业务代码。
"""
from .local import LocalStorage
from .kodo import KodoStorage

_cache: dict[str, object] = {}


def get_storage():
    """返回当前生效的存储实现（进程内缓存，配置变更后最多 60s 收敛）。"""
    from .. import config_service
    name = (config_service.get_text("media_provider") or "local").strip().lower()
    if name not in ("local", "kodo"):
        name = "local"
    impl = _cache.get(name)
    if impl is None:
        impl = KodoStorage() if name == "kodo" else LocalStorage()
        _cache[name] = impl
    return impl


def reset_cache() -> None:
    _cache.clear()
