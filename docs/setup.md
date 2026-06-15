## 📌 Project Overview

This application follows a standard Flask architecture using an application factory pattern.

This project demonstrates:
- Backend development with Flask
- Database integration with PostgreSQL
- Containerized development using Docker
- Testing and CI workflows

---

##  Features
- Flash messages for feedback
- Docker-based environment setup
- Automated testing using `pytest`
- Continuous Integration with GitHub Actions

---

## Tech Stack

- **Backend:** Flask
- **Database:** PostgreSQL
- **ORM:** SQLAlchemy (Flask-SQLAlchemy)
- **Migrations:** Flask-Migrate
- **Testing:** pytest
- **Environment Variables:** python-dotenv
- **Containerization:** Docker & Docker Compose
- **CI/CD:** GitHub Actions

---

## 🧑‍💻 Getting Started

### 1. Clone the Repository

```bash
git clone repository
cd Team_SGD
```
### 2. Setting environment variable in local seetings
```bash
cp .env_sample .env
```
### 3. Run with Docker
```bash
docker compose up --build
```
### 4. Open Application
```bash
http://localhost:5000
```
### 5. Open another terminal and start tailwind in watch mode
Start Tailwind watch mode:

```bash
npx @tailwindcss/cli -i ./app/static/src/input.css -o ./app/static/css/output.css --watch
```

This automatically rebuilds CSS whenever changes are made.

---

## Opening the Project in Codespaces

1. Open the repository on GitHub
2. Click:

```text
Code → Codespaces → Create codespace on main
```

3. Wait for the dev container to finish configuring

The dev container automatically:

- installs Node.js
- installs npm packages
- starts Docker services
- forwards ports 5000 and 5432

4. For continuous coding
   (i) "docker compose up" and Always "git pill" before "docker compose build", so as to update to latest changes in the repository

---

## Project Stack

- Flask
- PostgreSQL
- Docker Compose
- Tailwind CSS
- GitHub Codespaces

---

Check running containers:

```bash
docker ps
```

---
Expected containers:

```text
team_sgd-web-1
team_sgd-db-1
```

---

## Running Tailwind CSS

Start Tailwind watch mode:

```bash
npx @tailwindcss/cli -i ./app/static/src/input.css -o ./app/static/css/output.css --watch
```

This automatically rebuilds CSS whenever changes are made.

---

## Accessing the Application

Flask app:

```text
http://localhost:5000
```

PostgreSQL:

```text
localhost:5432
```

---

## Useful Docker Commands

Stop containers:

```bash
docker compose down
```

Restart containers:

```bash
docker compose restart
```

Rebuild containers:

```bash
docker compose up --build
```

View logs:

```bash
docker compose logs
```

View web logs only:

```bash
docker compose logs web
```

---

# Recommended Workflow

## Frontend Development

```bash
npx @tailwindcss/cli -i ./app/static/src/input.css -o ./app/static/css/output.css --watch
```

---

# Important Notes

- Do NOT commit `.env`
- Do NOT commit `node_modules`
- Do NOT commit `__pycache__`
- Commit migration files after successful migrations

---


