# Database Design

## Overview

HabitMind stores user information, habit selections, check-ins, and generated insights in PostgreSQL.

---

## Entity Relationship Overview

```text
User
 │
 ├── UserHabit
 │       ↓
 │     Habit
 │
 ├── CheckIn
 │       ↓
 │   CheckInHabit
 │       ↓
 │      Habit
 │
 ├── CurrentInsight
 │
 └── InsightReport
         ↓
    PremiumInsight
```

---

## User

Stores account information.

Fields:

* id
* name
* email
* password_hash
* plan
* reflection_tone
* onboarding_completed
* created_at

---

## Habit

Stores available habits.

Fields:

* id
* name
* category
* icon
* is_active

---

## UserHabit

Stores habits selected by a user.

Fields:

* id
* user_id
* habit_id
* created_at

---

## CheckIn

Stores mood check-ins.

Fields:

* id
* user_id
* mood_score
* date
* created_at

Constraint:

* One check-in per user per day

---

## CheckInHabit

Stores completed habits for a check-in.

Fields:

* id
* checkin_id
* habit_id

---

## CurrentInsight

Used for free users.

Fields:

* period_start
* period_end
* average_mood
* checkin_count
* top_habits_json
* what_we_noticed

Only one record is kept and it is written over in the next checked-in insight not stored continously

---

## InsightReport

Used for premium users.

Fields:

* period_start
* period_end
* average_mood
* checkin_count
* top_habits_json
* what_we_noticed
* goals_snapshot
* habits_snapshot_json

Historical reports are retained.

---

## PremiumInsight

Stores premium-only features.

Fields:

* reflection_text
* reflection_source
* recommendations_json
* recommendation_source
* location_latitude
* location_longitude
* location_label

Premium insight data is saved as a snapshot so results remain consistent over time.
