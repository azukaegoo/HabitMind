# HabitMind

HabitMind is a habit and mood tracking web application that helps users understand how their daily routines influence their emotional well-being.

Users complete daily check-ins by recording their mood and selecting the habits they completed. HabitMind analyzes this data and generates weekly insights that highlight patterns between habits and mood trends.

The platform supports both Free and Premium experiences. Free users receive basic insights, while Premium users gain access to personalized reflections, activity recommendations, insight history, and data export features.

---

## Features

### User Accounts

* User registration and login
* Secure password hashing
* Protected authenticated routes
* User profile management

### Habit Tracking

Users can track habits across multiple wellness categories.

#### Physical

* Exercise for 30 minutes
* Walk 8k+ steps
* Stretch or practice yoga

#### Sleep

* Sleep 7+ hours
* Keep a consistent bedtime
* Avoid screens before bed

#### Nutrition

* Drink 2L of water
* Eat fruits or vegetables
* Avoid junk food

#### Mental

* Meditate or practice breathing exercises
* Journal
* Spend time outdoors

#### Social

* Connect with someone
* Limit social media
* Help someone

#### Growth

* Read for 20 minutes
* Learn something new
* Practice gratitude

### Mood Check-ins

* Mood rating from 1-10
* One check-in per day
* Habit selection during check-in
* Streak tracking
* Average mood tracking

### Weekly Insights

After at least five check-ins, HabitMind generates:

* Average mood score
* Top habits associated with higher moods
* Habit pattern observations
* Weekly mood summary

### Premium Features

Premium users receive:

* Personalized reflections
* Reflection tone selection:
  * Supportive
  * Balanced
  * Challenging
* Personalized activity recommendations
* Insight history
* Data export
* Location-based recommendations (planned)

---

## Subscription Plans

### Free Plan

* Daily check-ins
* Mood tracking
* Habit tracking
* Weekly insights
* Current insight only, without history

### Premium Plan

* Everything in Free
* Personalized reflections
* Activity recommendations
* Insight history
* Data export
* Future location-based recommendations

---

## Technology Stack

### Backend

* Python
* Flask
* Flask-Login
* Flask-SQLAlchemy
* PostgreSQL

### Frontend

* HTML
* Tailwind CSS
* Jinja2 templates

### Development Tools

* Docker
* Docker Compose
* Git
* GitHub
* GitHub Actions
* pytest

---

## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/azukaegoo/Team_SGD.git
cd Team_SGD
```

### 2. Create Environment Variables

```bash
cp .env_sample .env
```

Update `.env` with the local values required for your development environment.

### 3. Run the Application

```bash
docker compose up --build
```

Open the app at:

```text
http://localhost:5000
```

### 4. Run Tailwind in Watch Mode

In a separate terminal, run:

```bash
npx @tailwindcss/cli -i ./app/static/src/input.css -o ./app/static/css/output.css --watch
```

This rebuilds the CSS whenever frontend styles change.

### 5. Run Tests

```bash
pytest
```

---

## Future Enhancements

* Ticketmaster activity integration
* OpenStreetMap location recommendations
* Advanced habit analytics
* Goal-specific recommendations
* Mobile application support
* Social accountability features

---

## Team Roles

### Human Members

* Define the design system and application architecture
* Implement and integrate features
* Review and test code before merging
* Manage GitHub branches and pull requests

### AI Assistance

* Assist with debugging errors, including Docker and database issues
* Help generate tests when needed
* Support documentation and code review workflows

AI is used as a development assistant, while all final decisions remain with the team.

---

## Development Workflow

To keep the project aligned:

* The team agrees on architecture and design decisions before implementation.
* GitHub is used for version control, pull requests, and tracking changes.
* Code reviews help maintain consistency and correctness.
* Tests are run with `pytest` to validate functionality.

---

## Documentation

* [Setup Guide](docs/setup.md)
* [Architecture](docs/architecture.md)
* [Database Documentation](docs/database.md)
