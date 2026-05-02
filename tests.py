#!/usr/bin/env python
from datetime import datetime, timezone, timedelta
import unittest
from unittest.mock import patch
import sqlalchemy as sa
from app import create_app, db
from app.models import User, Post, Message
from config import Config


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    WTF_CSRF_ENABLED = False
    SECRET_KEY = 'test-secret-key'


# ── helpers ───────────────────────────────────────────────────────────────────

def _create_user(username, email, password='password'):
    u = User(username=username, email=email)
    u.set_password(password)
    db.session.add(u)
    db.session.commit()
    return u


def _login(client, username, password='password'):
    return client.post('/auth/login', data={
        'username': username,
        'password': password,
    }, follow_redirects=True)


def _logout(client):
    return client.get('/auth/logout', follow_redirects=True)


# ── User model ────────────────────────────────────────────────────────────────

class UserModelCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_password_hashing(self):
        u = User(username='susan', email='susan@example.com')
        u.set_password('cat')
        self.assertFalse(u.check_password('dog'))
        self.assertTrue(u.check_password('cat'))

    def test_avatar(self):
        u = User(username='john', email='john@example.com')
        self.assertEqual(u.avatar(128), ('https://www.gravatar.com/avatar/'
                                         'd4c74594d841139328695756648b6bd6'
                                         '?d=identicon&s=128'))

    def test_follow(self):
        u1 = User(username='john', email='john@example.com')
        u2 = User(username='susan', email='susan@example.com')
        db.session.add(u1)
        db.session.add(u2)
        db.session.commit()
        following = db.session.scalars(u1.following.select()).all()
        followers = db.session.scalars(u2.followers.select()).all()
        self.assertEqual(following, [])
        self.assertEqual(followers, [])

        u1.follow(u2)
        db.session.commit()
        self.assertTrue(u1.is_following(u2))
        self.assertEqual(u1.following_count(), 1)
        self.assertEqual(u2.followers_count(), 1)
        u1_following = db.session.scalars(u1.following.select()).all()
        u2_followers = db.session.scalars(u2.followers.select()).all()
        self.assertEqual(u1_following[0].username, 'susan')
        self.assertEqual(u2_followers[0].username, 'john')

        u1.unfollow(u2)
        db.session.commit()
        self.assertFalse(u1.is_following(u2))
        self.assertEqual(u1.following_count(), 0)
        self.assertEqual(u2.followers_count(), 0)

    def test_follow_posts(self):
        u1 = User(username='john', email='john@example.com')
        u2 = User(username='susan', email='susan@example.com')
        u3 = User(username='mary', email='mary@example.com')
        u4 = User(username='david', email='david@example.com')
        db.session.add_all([u1, u2, u3, u4])

        now = datetime.now(timezone.utc)
        p1 = Post(body="post from john", author=u1,
                  timestamp=now + timedelta(seconds=1))
        p2 = Post(body="post from susan", author=u2,
                  timestamp=now + timedelta(seconds=4))
        p3 = Post(body="post from mary", author=u3,
                  timestamp=now + timedelta(seconds=3))
        p4 = Post(body="post from david", author=u4,
                  timestamp=now + timedelta(seconds=2))
        db.session.add_all([p1, p2, p3, p4])
        db.session.commit()

        u1.follow(u2)  # john follows susan
        u1.follow(u4)  # john follows david
        u2.follow(u3)  # susan follows mary
        u3.follow(u4)  # mary follows david
        db.session.commit()

        f1 = db.session.scalars(u1.following_posts()).all()
        f2 = db.session.scalars(u2.following_posts()).all()
        f3 = db.session.scalars(u3.following_posts()).all()
        f4 = db.session.scalars(u4.following_posts()).all()
        self.assertEqual(f1, [p2, p4, p1])
        self.assertEqual(f2, [p2, p3])
        self.assertEqual(f3, [p3, p4])
        self.assertEqual(f4, [p4])

    def test_password_reset_token(self):
        u = _create_user('alice', 'alice@example.com')
        token = u.get_reset_password_token()
        self.assertIsNotNone(token)
        verified = User.verify_reset_password_token(token)
        self.assertEqual(verified.id, u.id)

    def test_password_reset_token_invalid(self):
        result = User.verify_reset_password_token('not-a-valid-token')
        self.assertIsNone(result)

    def test_follow_does_not_duplicate(self):
        u1 = _create_user('john', 'john@example.com')
        u2 = _create_user('susan', 'susan@example.com')
        u1.follow(u2)
        u1.follow(u2)
        db.session.commit()
        self.assertEqual(u1.following_count(), 1)

    def test_unfollow_when_not_following(self):
        u1 = _create_user('john', 'john@example.com')
        u2 = _create_user('susan', 'susan@example.com')
        u1.unfollow(u2)  # should not raise
        db.session.commit()
        self.assertEqual(u1.following_count(), 0)


# ── Message model ─────────────────────────────────────────────────────────────

class MessageModelCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_message_creation(self):
        u1 = _create_user('alice', 'alice@example.com')
        u2 = _create_user('bob', 'bob@example.com')
        m = Message(sender=u1, recipient=u2, body='hello bob')
        db.session.add(m)
        db.session.commit()
        sent = db.session.scalars(u1.messages_sent.select()).all()
        received = db.session.scalars(u2.messages_received.select()).all()
        self.assertEqual(len(sent), 1)
        self.assertEqual(len(received), 1)
        self.assertEqual(sent[0].body, 'hello bob')

    def test_message_default_unread(self):
        u1 = _create_user('alice', 'alice@example.com')
        u2 = _create_user('bob', 'bob@example.com')
        m = Message(sender=u1, recipient=u2, body='are you there?')
        db.session.add(m)
        db.session.commit()
        self.assertFalse(m.read)

    def test_message_mark_read(self):
        u1 = _create_user('alice', 'alice@example.com')
        u2 = _create_user('bob', 'bob@example.com')
        m = Message(sender=u1, recipient=u2, body='read me')
        db.session.add(m)
        db.session.commit()
        m.read = True
        db.session.commit()
        self.assertTrue(m.read)

    def test_message_repr(self):
        u1 = _create_user('alice', 'alice@example.com')
        u2 = _create_user('bob', 'bob@example.com')
        m = Message(sender=u1, recipient=u2, body='hello')
        self.assertIn('hello', repr(m))

    def test_message_embedding_field(self):
        u1 = _create_user('alice', 'alice@example.com')
        u2 = _create_user('bob', 'bob@example.com')
        m = Message(sender=u1, recipient=u2, body='embed me',
                    embedding='[0.1, 0.2]')
        db.session.add(m)
        db.session.commit()
        fetched = db.session.get(Message, m.id)
        self.assertEqual(fetched.embedding, '[0.1, 0.2]')


# ── Post model ────────────────────────────────────────────────────────────────

class PostModelCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_post_creation(self):
        u = _create_user('john', 'john@example.com')
        p = Post(body='hello world', author=u)
        db.session.add(p)
        db.session.commit()
        posts = db.session.scalars(u.posts.select()).all()
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0].body, 'hello world')

    def test_post_repr(self):
        u = _create_user('john', 'john@example.com')
        p = Post(body='test repr', author=u)
        self.assertIn('test repr', repr(p))

    def test_post_embedding_field(self):
        u = _create_user('john', 'john@example.com')
        p = Post(body='embedding test', author=u, embedding='[0.1, 0.2, 0.3]')
        db.session.add(p)
        db.session.commit()
        fetched = db.session.get(Post, p.id)
        self.assertEqual(fetched.embedding, '[0.1, 0.2, 0.3]')

    def test_post_author_relationship(self):
        u = _create_user('john', 'john@example.com')
        p = Post(body='authored post', author=u)
        db.session.add(p)
        db.session.commit()
        self.assertEqual(p.author.username, 'john')

    def test_post_language_field(self):
        u = _create_user('john', 'john@example.com')
        p = Post(body='bonjour', author=u, language='fr')
        db.session.add(p)
        db.session.commit()
        fetched = db.session.get(Post, p.id)
        self.assertEqual(fetched.language, 'fr')


# ── Auth routes ───────────────────────────────────────────────────────────────

class AuthRoutesCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_register(self):
        rv = self.client.post('/auth/register', data={
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'secret123',
            'password2': 'secret123',
        }, follow_redirects=True)
        self.assertEqual(rv.status_code, 200)
        u = db.session.scalar(sa.select(User).where(User.username == 'newuser'))
        self.assertIsNotNone(u)

    def test_login_logout(self):
        _create_user('alice', 'alice@example.com', 'pass123')
        rv = _login(self.client, 'alice', 'pass123')
        self.assertEqual(rv.status_code, 200)
        rv = _logout(self.client)
        self.assertEqual(rv.status_code, 200)

    def test_login_wrong_password(self):
        _create_user('alice', 'alice@example.com', 'pass123')
        rv = _login(self.client, 'alice', 'wrongpass')
        self.assertIn(b'Invalid username or password', rv.data)

    def test_login_unknown_user(self):
        rv = _login(self.client, 'nobody', 'pass')
        self.assertIn(b'Invalid username or password', rv.data)

    def test_register_duplicate_username(self):
        _create_user('alice', 'alice@example.com')
        rv = self.client.post('/auth/register', data={
            'username': 'alice',
            'email': 'other@example.com',
            'password': 'password',
            'password2': 'password',
        }, follow_redirects=True)
        self.assertIn(b'Please use a different username', rv.data)

    def test_register_duplicate_email(self):
        _create_user('alice', 'alice@example.com')
        rv = self.client.post('/auth/register', data={
            'username': 'alice2',
            'email': 'alice@example.com',
            'password': 'password',
            'password2': 'password',
        }, follow_redirects=True)
        self.assertIn(b'Please use a different email address', rv.data)

    def test_unauthenticated_redirect(self):
        rv = self.client.get('/', follow_redirects=True)
        self.assertIn(b'Sign In', rv.data)


# ── Main routes ───────────────────────────────────────────────────────────────

class MainRoutesCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        self.client = self.app.test_client()
        self.u1 = _create_user('john', 'john@example.com')
        self.u2 = _create_user('susan', 'susan@example.com')

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_index_authenticated(self):
        _login(self.client, 'john')
        rv = self.client.get('/')
        self.assertEqual(rv.status_code, 200)

    @patch('app.main.routes.embed_to_json', return_value=None)
    def test_create_post(self, _mock):
        _login(self.client, 'john')
        rv = self.client.post('/', data={'post': 'hello from test'},
                              follow_redirects=True)
        self.assertEqual(rv.status_code, 200)
        p = db.session.scalar(sa.select(Post).where(Post.body == 'hello from test'))
        self.assertIsNotNone(p)
        self.assertEqual(p.author.username, 'john')

    def test_user_profile(self):
        _login(self.client, 'john')
        rv = self.client.get('/user/john')
        self.assertEqual(rv.status_code, 200)
        self.assertIn(b'john', rv.data)

    def test_user_profile_not_found(self):
        _login(self.client, 'john')
        rv = self.client.get('/user/nobody')
        self.assertEqual(rv.status_code, 404)

    def test_edit_profile(self):
        _login(self.client, 'john')
        rv = self.client.post('/edit_profile', data={
            'username': 'john',
            'about_me': 'I love testing',
        }, follow_redirects=True)
        self.assertEqual(rv.status_code, 200)
        db.session.refresh(self.u1)
        self.assertEqual(self.u1.about_me, 'I love testing')

    def test_follow_via_http(self):
        _login(self.client, 'john')
        rv = self.client.post('/follow/susan', data={'submit': 'Submit'},
                              follow_redirects=True)
        self.assertEqual(rv.status_code, 200)
        db.session.refresh(self.u1)
        self.assertTrue(self.u1.is_following(self.u2))

    def test_unfollow_via_http(self):
        self.u1.follow(self.u2)
        db.session.commit()
        _login(self.client, 'john')
        rv = self.client.post('/unfollow/susan', data={'submit': 'Submit'},
                              follow_redirects=True)
        self.assertEqual(rv.status_code, 200)
        db.session.refresh(self.u1)
        self.assertFalse(self.u1.is_following(self.u2))

    def test_explore_page(self):
        _login(self.client, 'john')
        rv = self.client.get('/explore')
        self.assertEqual(rv.status_code, 200)

    def test_search_users(self):
        _login(self.client, 'john')
        rv = self.client.get('/search?q=john&type=users')
        self.assertEqual(rv.status_code, 200)
        self.assertIn(b'john', rv.data)

    def test_search_posts(self):
        _login(self.client, 'john')
        p = Post(body='a unique testable phrase', author=self.u1)
        db.session.add(p)
        db.session.commit()
        rv = self.client.get('/search?q=unique+testable+phrase&type=posts')
        self.assertEqual(rv.status_code, 200)
        self.assertIn(b'unique testable phrase', rv.data)


# ── Messages routes ───────────────────────────────────────────────────────────

class MessagesRoutesCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        self.client = self.app.test_client()
        self.u1 = _create_user('alice', 'alice@example.com')
        self.u2 = _create_user('bob', 'bob@example.com')

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_inbox_requires_login(self):
        rv = self.client.get('/messages/messages/bob', follow_redirects=True)
        self.assertIn(b'Sign In', rv.data)

    def test_inbox_loads(self):
        _login(self.client, 'alice')
        rv = self.client.get('/messages/messages/bob')
        self.assertEqual(rv.status_code, 200)

    @patch('app.messages.routes.embed_to_json', return_value=None)
    def test_send_message(self, _mock):
        _login(self.client, 'alice')
        rv = self.client.post('/messages/messages/bob', data={'body': 'hey bob!'},
                              follow_redirects=True)
        self.assertEqual(rv.status_code, 200)
        m = db.session.scalar(sa.select(Message).where(Message.body == 'hey bob!'))
        self.assertIsNotNone(m)
        self.assertEqual(m.sender.username, 'alice')
        self.assertEqual(m.recipient.username, 'bob')

    def test_message_history_json(self):
        m = Message(sender=self.u1, recipient=self.u2, body='old message')
        db.session.add(m)
        db.session.commit()
        _login(self.client, 'alice')
        rv = self.client.get(f'/messages/messages/bob/history?before_id={m.id + 1}')
        self.assertEqual(rv.status_code, 200)
        data = rv.get_json()
        self.assertIn('messages', data)
        self.assertEqual(data['messages'][0]['body'], 'old message')

    def test_message_history_empty(self):
        _login(self.client, 'alice')
        rv = self.client.get('/messages/messages/bob/history?before_id=1')
        self.assertEqual(rv.status_code, 200)
        data = rv.get_json()
        self.assertEqual(data['messages'], [])
        self.assertFalse(data['has_more'])

    def test_inbox_partner_not_found(self):
        _login(self.client, 'alice')
        rv = self.client.get('/messages/messages/nobody')
        self.assertEqual(rv.status_code, 404)


if __name__ == '__main__':
    unittest.main(verbosity=2)
