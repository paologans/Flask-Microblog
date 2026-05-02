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
| `app.main` | `/` | Feed, post creation, user profiles, follow/unfollow, search |
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

Uses the `openai` Python package pointed at OpenRouter's base URL (`https://openrouter.ai/api/v1`), model `openai/gpt-oss-120b:free`, reasoning enabled. Both functions share a `_client()` helper.

Two AI functions in `app/ai_improve.py`:
- `improve_post(text)` — called by `POST /improve-post`; improves a draft post in-place. Direct call, no retrieval.
- `summarize_conversation(messages, user_a, user_b)` — called by `POST /messages/<username>/summarize`; summarizes up to the last 10 messages (or however many exist) in chronological order. Format passed to LLM: `Username said: "body"` per line. Prompt asks for key topics, tone, and any conclusions/next steps.

### RAG Pipeline

**Embeddings (`app/embeddings.py`)** — wraps `sentence-transformers` with the `all-MiniLM-L6-v2` model (384 dimensions, ~90MB, downloaded on first use, then cached). Exposes `embed(text)`, `embed_to_json(text)`, and `embed_batch(texts)`.

**Retrieval (`app/retrieval.py`)** — loads all posts that have embeddings, computes cosine similarity in-memory via `scikit-learn`, and returns the top-k (default 5) excluding the requesting user's own posts.

**Storage** — `Post.embedding` is a `Text` column (nullable) storing a JSON-serialized float list. Works with SQLite — no PostgreSQL/pgvector required.

**On post creation** — `main/routes.py` calls `embed_to_json(body)` and stores it on the `Post` immediately.

**Seed** — `seed.py` batch-encodes all post bodies after creation using `embed_batch()` for efficiency.

The RAG pipeline (`app/retrieval.py`) is built and ready but not yet wired to any route — reserved for a future summarizer or discovery feature.

### Search (`GET /search`)

Search bar is centered in the navbar (visible to authenticated users only). Accepts `q` (query string) and `type` (`all` | `users` | `posts`, default `all`). Uses `SearchForm` with CSRF disabled (GET form).

Results are ranked by relationship tier using SQLAlchemy `case()` on the `followers` table:
- Tier 1 — mutual follows
- Tier 2 — one-way follow (either direction)
- Tier 3 — no connection

Users matched on `username` and `about_me`. Posts matched on `body`. Results template: `app/templates/search.html` — tab bar for type filter, relationship badges (Mutual / Following / Follows you) on each result.

### Inbox / Messaging

The inbox uses lazy-loading: `GET /messages/<username>` renders only the 20 most recent messages. Older messages are fetched via `GET /messages/<username>/history?before_id=<id>` (JSON), triggered by an `IntersectionObserver` on a sentinel div at the top of the message list.

`GET /messages/<username>/summarize` — retrieves up to the last 10 messages (however many exist) in chronological order and returns an AI summary. Uses system + user message structure: system sets the summarization role, user message contains the transcript as `Username said: "body"` lines. The "Summarize" button sits left of the Send button in the send bar; the summary appears in a dismissible card above the message list.

### i18n

Strings wrapped with `_()` or `_l()` are extracted via Babel. Translations live in `app/translations/<lang>/LC_MESSAGES/`. The active locale is resolved from `Accept-Language` headers against `Config.LANGUAGES = ['en', 'es']`.

## Key Files Added Beyond the Base Tutorial

| File | Purpose |
|---|---|
| `app/templates/search.html` | Search results page (users + posts, relationship badges, type tabs) |
| `app/ai_improve.py` | OpenRouter/Claude-backed post improvement with RAG context |
| `app/embeddings.py` | sentence-transformers wrapper (`all-MiniLM-L6-v2`) |
| `app/retrieval.py` | Cosine similarity retrieval over Post embeddings |
| `app/translate.py` | Microsoft Translator integration |
| `seed.py` | Full database seeder — 30 users, varied posts (phrases/sentences/paragraphs), 15 natural conversation templates with variable timing (seconds to days between messages), embeddings |
| `query_users.py` | CLI table of all users with stats |
