from datetime import datetime
import random


def generate_kot_number() -> str:
    """
    Example:
    KOT-20260720-5124
    """

    date = datetime.now().strftime("%Y%m%d")
    number = random.randint(1000, 9999)

    return f"KOT-{date}-{number}"