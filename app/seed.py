from . import db
from .models import Habit
from sqlalchemy import inspect


def seed_default_habits():
    inspector = inspect(db.engine)

    if not inspector.has_table("habits"):
        print("Skipping habit seed: habits table does not exist yet.")
        return

    default_habits = [
        ("Exercise 30 min", "Physical", "🏋️"),  # 1 - referencing to front-end on click button to match activities in db
        ("Walk 8k+ steps", "Physical", "🚶"),  # 2
        ("Stretch or yoga", "Physical", "🧘"),   # 3

        ("Sleep 7+ hours", "Sleep", "😴"),   # 4
        ("Consistent bedtime", "Sleep", "🕒"),   # 5
        ("No screens before bed", "Sleep", "📵"),    # 6

        ("Drink 2L water", "Nutrition", "💧"),   # 7
        ("Eat fruits or vegetables", "Nutrition", "🥗"),  # 8
        ("No junk food", "Nutrition", "🚫"),

        ("Meditation or breathing", "Mental", "🧘"),    # 9
        ("Journaling", "Mental", "📓"),   # 10
        ("Time outdoors", "Mental", "🌳"),   # 11

        ("Connect with someone", "Social", "👥"),    # 12
        ("Limit social media", "Social", "📵"),  # 13
        ("Help someone", "Social", "🤝"),    # 14

        ("Read 20 minutes", "Growth", "📚"),     # 15
        ("Learn something new", "Growth", "🧠"),     # 16
        ("Practice gratitude", "Growth", "🙏"),  # 18
    ]

    for name, category, icon in default_habits:

        existing = Habit.query.filter_by(
            name=name
        ).first()

        if not existing:
            db.session.add(
                Habit(
                    name=name,
                    category=category,
                    icon=icon,
                    is_active=True
                )
            )

    db.session.commit()
