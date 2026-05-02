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
