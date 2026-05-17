"""北京时间工具函数——独立模块，避免循环导入。"""
from datetime import datetime, timedelta, timezone

BEIJING_TZ = timezone(timedelta(hours=8))


def beijing_now() -> datetime:
    """返回当前北京时间（naive datetime，兼容 SQLite DateTime 列）。"""
    return datetime.now(BEIJING_TZ).replace(tzinfo=None)
