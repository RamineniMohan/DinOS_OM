from datetime import datetime

_counter = 0
_last_date = None


def generate_order_number() -> str:
    global _counter, _last_date

    today = datetime.now().strftime("%Y%m%d")

    if _last_date != today:
        _counter = 0
        _last_date = today

    _counter += 1
    return f"ORD-{today}-{_counter:04d}"