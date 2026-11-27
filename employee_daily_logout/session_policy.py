from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo


EASTERN = ZoneInfo('America/New_York')
CUTOFF = time(18, 30)


def cutoff_bounds(now):
    """Return the previous and next 18:30 Eastern cutoffs as UTC timestamps."""
    local_now = datetime.fromtimestamp(now, timezone.utc).astimezone(EASTERN)
    cutoff_date = local_now.date()
    if local_now.time().replace(tzinfo=None) < CUTOFF:
        cutoff_date -= timedelta(days=1)
    previous = datetime.combine(cutoff_date, CUTOFF, EASTERN)
    following = datetime.combine(cutoff_date + timedelta(days=1), CUTOFF, EASTERN)
    return previous.timestamp(), following.timestamp()
