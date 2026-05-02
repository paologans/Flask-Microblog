import sqlalchemy as sa
from app import create_app, db
from app.models import User, Post, Message

app = create_app()

with app.app_context():
    users = db.session.scalars(sa.select(User).order_by(User.id)).all()

    if not users:
        print('No users found.')
    else:
        print(f'{"ID":<5} {"Username":<20} {"Email":<35} {"Posts":<7} {"Followers":<10} {"Following":<10} {"Last Seen"}')
        print('-' * 100)
        for u in users:
            post_count = db.session.scalar(
                sa.select(sa.func.count()).where(Post.user_id == u.id)
            )
            follower_count = db.session.scalar(
                sa.select(sa.func.count()).select_from(u.followers.select().subquery())
            )
            following_count = db.session.scalar(
                sa.select(sa.func.count()).select_from(u.following.select().subquery())
            )
            last_seen = u.last_seen.strftime('%Y-%m-%d %H:%M') if u.last_seen else 'never'
            print(f'{u.id:<5} {u.username:<20} {u.email:<35} {post_count:<7} {follower_count:<10} {following_count:<10} {last_seen}')

        print('-' * 100)
        print(f'Total: {len(users)} users')
