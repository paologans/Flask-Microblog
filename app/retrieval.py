import json
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import sqlalchemy as sa
from app import db
from app.embeddings import embed


def find_similar_posts(text: str, exclude_user_id: int = None, k: int = 5) -> list:
    from app.models import Post

    query_vec = embed(text)

    stmt = sa.select(Post).where(Post.embedding.isnot(None))
    if exclude_user_id is not None:
        stmt = stmt.where(Post.user_id != exclude_user_id)

    posts = db.session.scalars(stmt).all()
    if not posts:
        return []

    embeddings = [json.loads(p.embedding) for p in posts]
    sims = cosine_similarity([query_vec], embeddings)[0]

    top_indices = np.argsort(sims)[-k:][::-1]
    return [posts[i] for i in top_indices]


def find_similar_messages(text: str, user_id: int, k: int = 8) -> list[dict]:
    from app.models import Message, User

    query_vec = embed(text)

    msgs = db.session.scalars(
        sa.select(Message).where(
            sa.and_(
                Message.embedding.isnot(None),
                sa.or_(
                    Message.sender_id == user_id,
                    Message.recipient_id == user_id,
                )
            )
        )
    ).all()

    if not msgs:
        return []

    embeddings = [json.loads(m.embedding) for m in msgs]
    sims = cosine_similarity([query_vec], embeddings)[0]

    top_indices = np.argsort(sims)[-k:][::-1]

    result = []
    for i in top_indices:
        m = msgs[i]
        sender = db.session.get(User, m.sender_id)
        recipient = db.session.get(User, m.recipient_id)
        result.append({
            'from': sender.username if sender else 'unknown',
            'to': recipient.username if recipient else 'unknown',
            'body': m.body,
            'timestamp': m.timestamp.strftime('%Y-%m-%d %H:%M'),
        })
    return result


def find_user_messages(user_id: int, partner_id: int = None, limit: int = 30) -> list[dict]:
    from app.models import Message, User

    if partner_id is not None:
        where_clause = sa.or_(
            sa.and_(Message.sender_id == user_id, Message.recipient_id == partner_id),
            sa.and_(Message.sender_id == partner_id, Message.recipient_id == user_id),
        )
    else:
        where_clause = sa.or_(
            Message.sender_id == user_id,
            Message.recipient_id == user_id,
        )

    msgs = db.session.scalars(
        sa.select(Message)
        .where(where_clause)
        .order_by(Message.timestamp.desc())
        .limit(limit)
    ).all()

    result = []
    for m in reversed(msgs):
        sender = db.session.get(User, m.sender_id)
        recipient = db.session.get(User, m.recipient_id)
        result.append({
            'from': sender.username if sender else 'unknown',
            'to': recipient.username if recipient else 'unknown',
            'body': m.body,
            'timestamp': m.timestamp.strftime('%Y-%m-%d %H:%M'),
        })
    return result
