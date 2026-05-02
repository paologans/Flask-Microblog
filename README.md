# Postmind

Postmind is an AI-infused social media web app built with Flask. From a simple blog, it grew into a more complete social platform with user accounts, short-form posts, following, private messaging, search, translation, recommendations, and AI assistance woven into the posting and conversation experience.

The name **Postmind** reflects the app's focus on thoughtful posting, intelligent discovery, and AI-assisted conversations.

## What It Does

Postmind combines a classic short-form social feed with AI-powered discovery and writing tools:

- User registration, login, logout, profile editing, and password reset by email.
- Short posts up to 140 characters with automatic language detection.
- Home feed built from your own posts and posts from people you follow.
- Follow and unfollow relationships with follower/following counts.
- Post likes with asynchronous like/unlike updates.
- Profile pages with Gravatar-based avatars, bios, last-seen timestamps, post history, and message links.
- Microsoft Translator-powered post translation, with graceful fallback when translation is not configured.
- Global search for users and posts, ranked by relationship closeness.
- A personalized **For You** page for recommended posts and users.
- Private direct messaging with conversation lists, lazy-loaded message history, and AI summaries.
- Floating AI assistant available across authenticated pages.
- AI post improvement flow that suggests tighter, clearer, more engaging drafts.
- Embedding-backed retrieval over posts and the current user's own messages for contextual AI answers.
- Seed data generator for demo users, posts, conversations, and embeddings.
- English and Spanish i18n support through Flask-Babel.

## AI Features

Postmind uses the `openai` Python SDK pointed at OpenRouter:

- Base URL: `https://openrouter.ai/api/v1`
- Model: `openai/gpt-oss-120b:free`
- API key: `OPENROUTER_API_KEY`

Current AI experiences include:

- **Improve with AI**: the post composer can open an AI assistant panel that rewrites a draft while keeping it under the app's 140-character post limit.
- **Floating assistant**: authenticated users can ask general questions from any page. When the question appears to ask about community posts or the user's own messages, the route retrieves relevant context before calling the model.
- **Conversation summaries**: message threads include a Summarize button that condenses recent messages into a short plain-language recap.
- **Retrieval-augmented context**: public posts and the current user's own messages are embedded and searched semantically. The assistant is instructed not to invent missing private-message content or reveal messages outside the current user's access.

## Recommendations And Retrieval

The recommendation layer is powered by local sentence embeddings:

- Embedding model: `sentence-transformers/all-MiniLM-L6-v2`
- Vector size: 384 dimensions
- Storage: JSON-serialized vectors in SQLite `Text` columns
- Similarity: in-memory cosine similarity with scikit-learn

The **For You** feed builds a user interest vector from:

- The user's own posts.
- Posts the user has liked.
- Posts by people the user follows.

The same embedding infrastructure supports semantic retrieval for chatbot context and message lookup.

## Core Routes

| Route | Purpose |
|---|---|
| `/` and `/index` | Home feed and post creation |
| `/explore` | Personalized For You posts and user recommendations |
| `/user/<username>` | Public profile and user post history |
| `/edit_profile` | Profile editing |
| `/follow/<username>` | Follow a user |
| `/unfollow/<username>` | Unfollow a user |
| `/like/<post_id>` | Toggle a post like |
| `/search?q=...&type=...` | Search users and posts |
| `/translate` | Translate a post |
| `/improve-post` | Direct AI post improvement endpoint |
| `/chat` | Floating assistant endpoint |
| `/messages` | Inbox and conversation list |
| `/messages/<username>` | Direct message thread |
| `/messages/<username>/history` | Lazy-load older messages as JSON |
| `/messages/<username>/summarize` | AI summary for a message thread |
| `/auth/login` | Login |
| `/auth/register` | Registration |
| `/auth/reset_password_request` | Request password reset email |
| `/auth/reset_password/<token>` | Reset password |

## Tech Stack

- Flask 3
- SQLAlchemy 2 and Flask-SQLAlchemy
- Flask-Migrate and Alembic
- Flask-Login
- Flask-WTF and WTForms
- Flask-Mail
- Flask-Moment
- Flask-Babel
- Bootstrap 5 and Bootstrap Icons
- OpenRouter through the OpenAI Python SDK
- sentence-transformers
- scikit-learn
- Microsoft Translator API
- SQLite by default, configurable through `DATABASE_URL`

## Project Structure

| Path | Purpose |
|---|---|
| `postmind.py` | Flask entry point and shell context |
| `config.py` | App configuration and environment variable loading |
| `app/__init__.py` | App factory, extensions, blueprint registration, logging |
| `app/models.py` | User, Post, Message, followers, and post likes models |
| `app/main/routes.py` | Feed, posting, profiles, following, likes, search, translation, AI chat |
| `app/messages/routes.py` | Inbox, direct messages, lazy history, AI summaries |
| `app/auth/routes.py` | Login, registration, logout, password reset |
| `app/ai_improve.py` | OpenRouter-backed AI post improvement, chatbot, summaries |
| `app/embeddings.py` | Sentence-transformers embedding helpers |
| `app/retrieval.py` | Semantic search and For You recommendation logic |
| `app/translate.py` | Microsoft Translator integration |
| `app/templates/` | Jinja templates and Bootstrap 5 UI |
| `migrations/` | Active Alembic migrations |
| `seed.py` | Demo data seeding with users, posts, messages, embeddings |
| `tests.py` | Unit and route tests |

## Environment Variables

Create a local `.env` file for secrets and service configuration.

| Variable | Required | Purpose |
|---|---:|---|
| `SECRET_KEY` | Recommended | Flask session signing |
| `DATABASE_URL` | No | Database URL; defaults to local SQLite `app.db` |
| `OPENROUTER_API_KEY` | Yes for AI | AI post improvement, assistant, message summaries |
| `MS_TRANSLATOR_KEY` | Yes for translation | Microsoft Translator integration |
| `MAIL_SERVER` | Yes for email | SMTP server for password reset |
| `MAIL_PORT` | Yes for email | SMTP port |
| `MAIL_USE_TLS` | Optional | Enable TLS when set |
| `MAIL_USERNAME` | Yes for email auth | SMTP username |
| `MAIL_PASSWORD` | Yes for email auth | SMTP password |

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
flask db upgrade
flask run
```

The sentence-transformers model downloads on first embedding use, then is cached locally by the underlying library.

## Demo Data

To create a populated local demo database:

```bash
python seed.py
```

The seeder creates 30 fake users, varied topic-based posts, natural-looking conversations, follow relationships, and embeddings for posts and messages.

To inspect users:

```bash
python query_users.py
```

## Tests

Run the test suite with:

```bash
python -m pytest tests.py
```

or:

```bash
python tests.py
```

## Database And Migrations

After model changes:

```bash
flask db migrate -m "description"
flask db upgrade
```

The current app uses the `migrations/` directory. The `migrations_old/` directory preserves older migration history from the base tutorial lineage.

## Translations

Postmind currently supports English and Spanish via Flask-Babel.

```bash
flask translate init <lang>
flask translate update
flask translate compile
```



## Credits

This project began as a version of Miguel Grinberg's Flask Mega-Tutorial application.

Postmind extends that foundation with messaging, search, recommendations, post likes, translation, AI writing assistance, AI chat, message summaries, embeddings, retrieval, seeded demo data, and expanded tests.
