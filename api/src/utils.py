import datetime


def _get_utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)
