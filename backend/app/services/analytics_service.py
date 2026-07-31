from collections import Counter
from datetime import timedelta

from app.models.feedback import FeedbackItem


def _week_start(item: FeedbackItem) -> str:
    return (item.feedback_date - timedelta(days=item.feedback_date.weekday())).isoformat()


def theme_analytics(items: list[FeedbackItem]) -> dict[str, object]:
    """Authoritative metrics; callers must pass only items linked by memberships."""
    sources = Counter(item.source for item in items)
    user_types = Counter(item.user_type for item in items)
    weeks = Counter(_week_start(item) for item in items)
    count = len(items)
    return {
        "member_count": count,
        "distribution_by_source": dict(sorted(sources.items())),
        "distribution_by_user_type": dict(sorted(user_types.items())),
        "frequency_over_time": [{"week_start": week, "count": weeks[week]} for week in sorted(weeks)],
        "recurrence": "recurring" if count >= 2 else "isolated",
    }
