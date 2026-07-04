from datetime import datetime, UTC, timedelta
from app.models import CheckIn


# ═══════════════════════════════════════════
# Helper functions
# ═══════════════════════════════════════════
def calculate_streak(user_id):
    today = datetime.now(UTC).date()

    checkins = (
        CheckIn.query
        .filter_by(user_id=user_id)
        .order_by(CheckIn.date.desc())
        .all()
    )

    if not checkins:
        return 0

    latest_date = checkins[0].date

    if latest_date == today:
        expected_date = today
    elif latest_date == today - timedelta(days=1):
        expected_date = today - timedelta(days=1)
    else:
        return 0

    streak = 0

    for checkin in checkins:
        if checkin.date == expected_date:
            streak += 1
            expected_date -= timedelta(days=1)
        else:
            break

    return streak


def get_mood_emoji(avg_mood):
    if avg_mood is None:
        return "—"

    rounded_mood = round(avg_mood)

    mood_emojis = {
        1: "😭",
        2: "😰",
        3: "😟",
        4: "🙁",
        5: "😐",
        6: "🙂",
        7: "😊",
        8: "😄",
        9: "😁",
        10: "🤩",
    }

    return mood_emojis.get(rounded_mood, "😐")