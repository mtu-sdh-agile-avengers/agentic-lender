from slowapi import Limiter
from slowapi.util import get_remote_address

from src.config import RunMode, get_config

limiter = Limiter(
    key_func=get_remote_address,
    strategy="fixed-window",
    storage_uri="memory://",
    enabled=True if get_config().run_mode == RunMode.PROD else False,   # rate limiting works only in production mode
)
