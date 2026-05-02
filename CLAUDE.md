# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the development server (FLASK_APP and FLASK_DEBUG=1 set in .flaskenv)
flask run

# Run tests
python -m pytest tests.py
python tests.py                        # alternative

# Database migrations
flask db migrate -m "description"
flask db upgrade

# Seed the database with 30 fake users, posts, and conversations
python seed.py

# Query all users in the database
python query_users.py

# Flask shell (exposes sa, so, db, User, Post)
flask shell

# i18n / translations
flask translate init <lang>            # add a new language
flask translate update                 # extract new strings
flask translate compile                # compile .po → .mo
```

## Environment Variables

Required in `.env` (never committed):

| Variable | Purpose |
|---|---|
| `OPENROUTER_API_KEY` | AI post improvement via OpenRouter (`app/ai_improve.py`) |
| `MS_TRANSLATOR_KEY` | Post translation via Microsoft Translator (`app/translate.py`) — optional, feature degrades gracefully |
| `SECRET_KEY` | Flask session signing |
| `DATABASE_URL` | Defaults to SQLite `app.db` if unset |
| `MAIL_SERVER` / `MAIL_PORT` / `MAIL_USERNAME` / `MAIL_PASSWORD` | Email (password reset) |

## Architecture

### App Factory & Blueprints

`app/__init__.py` exports `create_app()` and the shared extensions (`db`, `login`, `mail`, `moment`, `babel`). The app is composed of four blueprints:

| Blueprint | Prefix | Responsibility |
|---|---|---|
| `app.main` | `/` | Feed, post creation, user profiles, follow/unfollow |
| `app.auth` | `/auth` | Login, logout, registration, password reset |
| `app.messages` | `/messages` | Inbox, conversation view, message send, lazy-load history |
| `app.errors` | — | 404 / 500 handlers |

`microblog.py` at the root is the entry point — calls `create_app()` and registers shell context.

### Models (`app/models.py`)

Three tables: `User`, `Post`, `Message`. `followers` is an association table for the self-referential User→User many-to-many.

- `User.following_posts()` — returns a SQLAlchemy select query for the home feed (own posts + followed users' posts), used with `db.paginate()`
- `User.avatar(size)` — returns a Gravatar URL
- All relationships on `User` use `WriteOnlyMapped` (requires `.select()` to query, `.add()` / `.remove()` to mutate)
- All timestamps must be `datetime.now(timezone.utc)` — naive datetimes cause display bugs with Flask-Moment

### Templates

`app/templates/base.html` defines two extension points:
- `{% block outer_content %}` — overridden by `messages/inbox.html` to escape the Bootstrap `container mt-3` wrapper and render a full-viewport chat layout
- `{% block scripts %}` — for per-page JavaScript; `base.html` sets `--nav-h` CSS variable from the actual navbar height

`app/templates/bootstrap_wtf.html` is a local Bootstrap 5 macro library that replaces Flask-Bootstrap. Use `{{ wtf.quick_form(form) }}` to render a WTForms form.

### AI Feature (`app/ai_improve.py`)

Uses the `openai` Python package pointed at OpenRouter's base URL (`https://openrouter.ai/api/v1`). Currently uses model `openai/gpt-oss-120b:free`. The `POST /improve-post` route in `app/main/routes.py` calls this and returns JSON — the frontend replaces the textarea value in-place.

### Inbox / Messaging

The inbox uses lazy-loading: `GET /messages/<username>` renders only the 20 most recent messages. Older messages are fetched via `GET /messages/<username>/history?before_id=<id>` (JSON), triggered by an `IntersectionObserver` on a sentinel div at the top of the message list.

### i18n

Strings wrapped with `_()` or `_l()` are extracted via Babel. Translations live in `app/translations/<lang>/LC_MESSAGES/`. The active locale is resolved from `Accept-Language` headers against `Config.LANGUAGES = ['en', 'es']`.

## Key Files Added Beyond the Base Tutorial

| File | Purpose |
|---|---|
| `app/ai_improve.py` | OpenRouter-backed post improvement |
| `app/translate.py` | Microsoft Translator integration |
| `seed.py` | Full database seeder (30 users, posts, conversations) |
| `query_users.py` | CLI table of all users with stats |
