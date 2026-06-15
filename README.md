# HabitMind

HabitMind is a habit and mood tracking web application designed to help users understand how their daily habits influence their emotional well-being.

Users complete regular check-ins by recording their mood and selecting habits they completed. HabitMind analyzes this data and generates weekly insights that highlight patterns between habits and mood trends.

The platform offers both Free and Premium experiences. Free users receive basic insights, while Premium users gain access to personalized reflections, activity recommendations, insight history, and data export features.

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

* Exercise 30 min
* Walk 8k+ steps
* Stretch or yoga

#### Sleep

* Sleep 7+ hours
* Consistent bedtime
* No screens before bed

#### Nutrition

* Drink 2L water
* Eat fruits or vegetables
* No junk food

#### Mental

* Meditation or breathing
* Journaling
* Time outdoors

#### Social

* Connect with someone
* Limit social media
* Help someone

#### Growth

* Read 20 minutes
* Learn something new
* Practice gratitude

### Mood Check-ins

* Mood rating from 1–10
* One check-in per day
* Habit selection during check-in
* Streak tracking
* Average mood tracking

### Weekly Insights

After completing at least five check-ins, HabitMind generates:

* Average mood score
* Top habits associated with higher moods
* Habit pattern observations
* Weekly mood summary

### Premium Features

Premium users receive:

* Personalized reflections
* Reflection tone selection

  * Supportive
  * Balanced
  * Challenge
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
* Current insight only (no history)

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
* Jinja2 Templates

### Database

* PostgreSQL

### Development Tools

* Docker
* Docker Compose
* Git
* GitHub
* 
---

## Future Enhancements

* Ticketmaster activity integration
* OpenStreetMap location recommendations
* Advanced habit analytics
* Goal-specific recommendations
* Mobile application support
* Social accountability features

---

## Authors

HabitMind was developed as a wellness and habit-tracking platform focused on helping users build healthier routines and better understand the connection between habits and mood.

---
## Team Roles

#### Human Members
- Design system architecture
- Implement and integrate features
- Review and test all code before merging
- Manage GitHub branches and pull requests

#### AI Assistance
- Assists with debugging errors (e.g., Docker, database issues)
- Help generate tests when needed

AI is used as a development assistant, while all final decisions remain with the team.


### Ensuring Correct Direction

To ensure the project stays aligned:

- The team agrees on architecture and design decisions before implementation

- GitHub is used for:
  - version control
  - pull requests
  - tracking changes

- Code reviews ensure consistency and correctness
- Testing (`pytest`) is used to validate functionality

---
## Documentation

- [Setup Guide](docs/setup.md)
- [Architecture](docs/architecture.md)
- [API Documentation](docs/database.md)

