import json
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import sqlalchemy as sa
from app import db
from app.embeddings import embed


# Weights for user interest vector: own posts, liked posts, following's posts
_W_OWN = 0.50
_W_LIKES = 0.35
_W_FRIENDS = 0.15


def _avg_embeddings(posts: list) -> np.ndarray | None:
    vecs = [json.loads(p.embedding) for p in posts if p.embedding]
    if not vecs:
        return None
    return np.mean(vecs, axis=0)


def build_user_interest_vector(user) -> np.ndarray | None:
    from app.models import Post, post_likes

    own_posts = db.session.scalars(
        sa.select(Post).where(Post.user_id == user.id, Post.embedding.isnot(None))
    ).all()

    liked_posts = db.session.scalars(
        sa.select(Post)
        .join(post_likes, Post.id == post_likes.c.post_id)
        .where(post_likes.c.user_id == user.id, Post.embedding.isnot(None))
    ).all()

    from app.models import followers as followers_table
    following_ids = db.session.scalars(
        sa.select(followers_table.c.followed_id).where(
            followers_table.c.follower_id == user.id
        )
    ).all()

    friend_posts = []
    if following_ids:
        friend_posts = db.session.scalars(
            sa.select(Post).where(
                Post.user_id.in_(following_ids),
                Post.embedding.isnot(None)
            )
        ).all()

    own_vec = _avg_embeddings(own_posts)
    likes_vec = _avg_embeddings(liked_posts)
    friends_vec = _avg_embeddings(friend_posts)

    components = []
    weights = []
    if own_vec is not None:
        components.append(_W_OWN * own_vec)
        weights.append(_W_OWN)
    if likes_vec is not None:
        components.append(_W_LIKES * likes_vec)
        weights.append(_W_LIKES)
    if friends_vec is not None:
        components.append(_W_FRIENDS * friends_vec)
        weights.append(_W_FRIENDS)

    if not components:
        return None

    total_weight = sum(weights)
    combined = sum(components) / total_weight
    return combined


def find_for_you_posts(user, page: int = 1, per_page: int = 30):
    from app.models import Post

    interest_vec = build_user_interest_vector(user)

    stmt = sa.select(Post).where(
        Post.user_id != user.id,
        Post.embedding.isnot(None)
    )
    posts = db.session.scalars(stmt).all()

    if not posts:
        return [], 0

    if interest_vec is None:
        # Fallback: chronological
        all_posts = db.session.scalars(
            sa.select(Post).where(Post.user_id != user.id)
            .order_by(Post.timestamp.desc())
        ).all()
        total = len(all_posts)
        start = (page - 1) * per_page
        return all_posts[start:start + per_page], total

    embeddings = [json.loads(p.embedding) for p in posts]
    sims = cosine_similarity([interest_vec], embeddings)[0]
    order = np.argsort(sims)[::-1]
    sorted_posts = [posts[i] for i in order]

    total = len(sorted_posts)
    start = (page - 1) * per_page
    return sorted_posts[start:start + per_page], total


def find_for_you_users(user, limit: int = 10) -> list:
    from app.models import User, Post

    interest_vec = build_user_interest_vector(user)
    if interest_vec is None:
        return []

    other_users = db.session.scalars(
        sa.select(User).where(User.id != user.id)
    ).all()

    scored = []
    for u in other_users:
        user_posts = db.session.scalars(
            sa.select(Post).where(Post.user_id == u.id, Post.embedding.isnot(None))
        ).all()
        user_vec = _avg_embeddings(user_posts)
        if user_vec is None:
            continue
        sim = cosine_similarity([interest_vec], [user_vec])[0][0]
        scored.append((u, float(sim)))

    scored.sort(key=lambda x: x[1], reverse=True)
    return [u for u, _ in scored[:limit]]


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
