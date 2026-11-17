from slowapi import Limiter
from slowapi.util import get_remote_address

from src.config import RunMode, get_config

# ref: https://slowapi.readthedocs.io/en/latest/, https://slowapi.readthedocs.io/en/latest/api/
limiter = Limiter(
    key_func=get_remote_address,
    strategy="fixed-window",  # when the first request arrives, a window is started for a fixed duration; requests in that window increment the counter; counter resets when window expires
    storage_uri="memory://",  # request counters are stored in memory (RAM)
    enabled=get_config().run_mode
    == RunMode.PROD,  # rate limiting works only in production mode
)
