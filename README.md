# Home Chores Manager

A lightweight Django app that distributes household chores fairly across
roommates using a weighted point rotation, tracks weekly assignments, and
penalizes overdue tasks.

## Requirements

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) for dependency and environment management

## Setup

Install dependencies:

```bash
uv sync
```

Apply the database migrations:

```bash
uv run python manage.py migrate
```

## Seed demo data

Load a few demo roommates and chores (safe to re-run; existing records are
skipped):

```bash
uv run python manage.py seed_data
```

## Create and use the admin

Create a superuser for Django's admin portal:

```bash
uv run python manage.py createsuperuser
```

The admin lets you add and edit roommates, chores, and assignments.

## Run the app

Start the development server:

```bash
uv run python manage.py runserver
```

Then open:

- Dashboard: http://127.0.0.1:8000/
- Admin: http://127.0.0.1:8000/admin/

From the dashboard, use **Generate This Week's Chores** to create this week's
assignments, and the **Complete** button on each pending chore to mark it done.

## Run the tests

```bash
uv run python manage.py test
```
