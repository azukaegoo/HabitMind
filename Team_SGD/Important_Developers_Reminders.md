# Team SGD Development Guide

## Initial Setup

Clone the repository:

```bash
git clone
cd DPD_Team_SGD
```

---


Start the Docker containers:

```bash
docker compose up
```

Open the app in browser:

```txt
http://localhost:5000
```

---

# Frontend Development (Tailwind CSS)

Tailwind CSS requires a second terminal running in watch mode.

## Terminal 1

Run Docker:

```bash
docker compose up
```

## Terminal 2

Run Tailwind watcher:

```bash
npx @tailwindcss/cli -i ./app/static/src/input.css -o ./app/static/css/output.css --watch
```

---

# Frontend Workflow

```txt
Edit template
Save file
Refresh browser
```

If styles do not update, Although it does, it has been tested, Just Incase:

```txt
Ctrl + F5
```

---

# Important Frontend Notes

Do NOT edit:

```txt
app/static/css/output.css
```

Tailwind automatically generates this file.

Custom CSS should be written inside:

```txt
app/static/src/input.css
```

Flask templates are inside:

```txt
app/templates/
```

---

# Backend Development

## Flask-Migrate Commands

If you change database models:

- add table
- add column
- remove column
- modify field type

then create a migration:

```bash
docker compose exec web flask db migrate -m "describe change"
```

Apply migration:

```bash
docker compose exec web flask db upgrade
```

Check migration status:

```bash
docker compose exec web flask db current
```

---

# Migration Notes

Do NOT run:

```bash
flask db init
```

again unless the `migrations/` folder does not exist.

Always commit migration files:

```bash
git add migrations
git commit -m "Add migration"
git push
```

---

# Docker Notes

Safe shutdown:

```bash
docker compose down
```

Dangerous command:

```bash
docker compose down -v
```

The `-v` option deletes the PostgreSQL database volume and removes local database data.

---

# Daily Development Workflow

## Start of Work

```bash
docker compose up
```

Open second terminal:

```bash
npx @tailwindcss/cli -i ./app/static/src/input.css -o ./app/static/css/output.css --watch
```

---

## End of Work

Stop containers:

```bash
docker compose down
```

Commit changes:

```bash
git add .
git commit -m "Describe changes"
git push
```
