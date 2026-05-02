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

Three AI functions in `app/ai_improve.py`:
- `improve_post(text)` — called by `POST /improve-post`; improves a draft post in-place. Direct call, no retrieval.
- `chat_response(message, history, username, post_context, message_context)` — called by `POST /chat`; powers the floating chatbot. Builds a system prompt with platform context and any retrieved content, then appends the full conversation history before the current message. Intent detection in the route determines which context to retrieve.
- `summarize_conversation(messages, user_a, user_b)` — called by `GET /messages/<username>/summarize`; summarizes up to the last 10 messages (or however many exist) in chronological order. Format passed to LLM: `Username said: "body"` per line. Prompt asks for key topics, tone, and any conclusions/next steps.

### RAG Pipeline

**Embeddings (`app/embeddings.py`)** — wraps `sentence-transformers` with the `all-MiniLM-L6-v2` model (384 dimensions, ~90MB, downloaded on first use, then cached). Exposes `embed(text)`, `embed_to_json(text)`, and `embed_batch(texts)`.

**Retrieval (`app/retrieval.py`)** — loads all posts that have embeddings, computes cosine similarity in-memory via `scikit-learn`, and returns the top-k (default 5) excluding the requesting user's own posts.

**Storage** — `Post.embedding` is a `Text` column (nullable) storing a JSON-serialized float list. Works with SQLite — no PostgreSQL/pgvector required.

**On post creation** — `main/routes.py` calls `embed_to_json(body)` and stores it on the `Post` immediately.

**Seed** — `seed.py` batch-encodes all post bodies after creation using `embed_batch()` for efficiency.

The RAG pipeline (`app/retrieval.py`) powers both post and message retrieval for the chatbot:
- `find_similar_posts(text, k=5)` — semantic search over post embeddings
- `find_similar_messages(text, user_id, k=8)` — semantic search over the current user's message embeddings only; never accesses other users' messages
- `find_user_messages(user_id, partner_id=None)` — recent message fetch used by the conversation summarizer

**For You feed (`app/retrieval.py`)** — personalized recommendation pipeline:
- `build_user_interest_vector(user)` — weighted average of the user's own post embeddings (50%), liked post embeddings (35%), and posts from users they follow (15%). Re-normalizes if any signal is missing. Returns `None` if no signals exist.
- `find_for_you_posts(user, page, per_page)` — ranks all posts (excluding the user's own) by cosine similarity to the interest vector; returns `(posts, total)` for pagination. Falls back to chronological if interest vector is `None`.
- `find_for_you_users(user, limit=10)` — scores all other users by comparing their average post embedding to the current user's interest vector; returns top `limit` by similarity.

`Message.embedding` (Text, nullable) stores JSON-serialised vectors, same pattern as `Post.embedding`. Generated on send in `messages/routes.py` and batch-generated in `seed.py`.

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

## Development Guidelines

### Workflow
- Always run `python -m pytest tests.py` after any code change before marking a task done
- Always run `flask db migrate -m "description"` + `flask db upgrade` after any model change
- Never add a new pip dependency without asking the user first
- Never push to remote without explicit user confirmation
- Never delete files or drop database tables without asking first

### Code Style
- Follow existing patterns in the file being edited — don't introduce new abstractions unless the task requires it
- All new timestamps must use `datetime.now(timezone.utc)` — never naive datetimes
- Keep new routes inside the existing blueprint structure (`main`, `auth`, `messages`, `errors`) — don't create new blueprints without discussion

### UI / Templates
- All new templates must use Bootstrap 5 components and match the existing card/form/button patterns
- Use the local `bootstrap_wtf.html` macro (`{{ wtf.quick_form(form) }}`) for all WTForms rendering — do not inline raw HTML form fields
- JavaScript goes in `{% block scripts %}` — never inline `<script>` tags outside that block

### AI & External Services
- Always use OpenRouter (`https://openrouter.ai/api/v1`) via the `openai` Python package — never call Anthropic or OpenAI APIs directly
- Never store raw API responses in the database
- New AI features follow the pattern in `app/ai_improve.py` — shared `_client()` helper, model `openai/gpt-oss-120b:free`

### Refer to Official Documentation
When implementing or debugging features, always consult the official docs for the relevant library (see section below) rather than relying on assumptions or outdated patterns.

---

## Official Documentation

| Library / Framework | Docs URL |
|---|---|
| Flask | https://flask.palletsprojects.com/en/stable/ |
| SQLAlchemy | https://docs.sqlalchemy.org/en/20/ |
| Flask-SQLAlchemy | https://flask-sqlalchemy.palletsprojects.com/en/stable/ |
| Flask-Migrate (Alembic) | https://flask-migrate.readthedocs.io/en/latest/ |
| Flask-Login | https://flask-login.readthedocs.io/en/latest/ |
| Flask-WTF / WTForms | https://flask-wtf.readthedocs.io/en/stable/ |
| Flask-Mail | https://flask-mail.readthedocs.io/en/latest/ |
| Flask-Moment | https://flask-moment.readthedocs.io/en/latest/ |
| Flask-Babel | https://python-babel.github.io/flask-babel/ |
| Jinja2 | https://jinja.palletsprojects.com/en/stable/ |
| Bootstrap 5 | https://getbootstrap.com/docs/5.3/ |
| sentence-transformers | https://www.sbert.net/docs/ |
| scikit-learn | https://scikit-learn.org/stable/documentation.html |
| openai Python SDK | https://platform.openai.com/docs/libraries/python-library |
| OpenRouter API | https://openrouter.ai/docs |

---

## Key Files Added Beyond the Base Tutorial

| File | Purpose |
|---|---|
| `app/templates/search.html` | Search results page (users + posts, relationship badges, type tabs) |
| `app/templates/for_you.html` | For You page — Posts tab (paginated, similarity-ranked) and Users tab (top 10 by interest match) |
| `app/templates/base.html` | Floating chat widget (bottom-right FAB → chat box, all pages) |
| `app/ai_improve.py` | OpenRouter/Claude-backed post improvement with RAG context |
| `app/embeddings.py` | sentence-transformers wrapper (`all-MiniLM-L6-v2`) |
| `app/retrieval.py` | Cosine similarity retrieval over Post embeddings; For You feed ranking (`build_user_interest_vector`, `find_for_you_posts`, `find_for_you_users`) |
| `app/translate.py` | Microsoft Translator integration |
| `seed.py` | Full database seeder — 30 users, varied posts (phrases/sentences/paragraphs), 15 natural conversation templates with variable timing (seconds to days between messages), embeddings |
| `query_users.py` | CLI table of all users with stats |
