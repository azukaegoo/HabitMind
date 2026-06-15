# HabitMind Architecture

## Overview

HabitMind is a Flask-based web application that helps users track habits, monitor mood, and generate weekly insights based on their behavior patterns.

The application follows a traditional web architecture:

```text
Browser
    ↓
Flask Routes
    ↓
Business Logic
    ↓
SQLAlchemy Models
    ↓
PostgreSQL Database
```

---

## User Flow

```text
Register
    ↓
Login
    ↓
Complete Onboarding
    ↓
Select Goals
    ↓
Select Habits
    ↓
Daily Check-ins
    ↓
Insight Generation
```

---

## Insight Flow

```text
User completes check-in
        ↓
Mood score saved
        ↓
Selected habits saved
        ↓
Check-in history analyzed
        ↓
Top habits identified
        ↓
Average mood calculated
        ↓
Insight generated
```

### Free Users

```text
Current Insight
        ↓
Replaced when a new insight is generated
```

### Premium Users

```text
Insight Report
        ↓
Premium Reflection
        ↓
Recommendations
        ↓
Saved to Insight History
```

---

## Premium Architecture

Premium features are built on top of the standard insight system.

```text
InsightReport
        ↓
PremiumInsight
            ├── Reflection
            ├── Recommendations
            └── Location Snapshot
```

Premium users retain historical reports while free users only keep the latest insight.

---

## Technology Stack

### Frontend

* HTML
* Tailwind CSS
* Jinja2 Templates

### Backend

* Python
* Flask
* Flask-Login
* SQLAlchemy

### Database

* PostgreSQL

### Infrastructure

* Docker
* Docker Compose
* GitHub
