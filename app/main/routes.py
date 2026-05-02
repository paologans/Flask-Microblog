from datetime import datetime, timezone
import re
from flask import render_template, flash, redirect, url_for, request, g, \
    current_app
from flask_login import current_user, login_required
from flask_babel import _, get_locale
import sqlalchemy as sa
import sqlalchemy.orm as so
from langdetect import detect, LangDetectException
from app import db
from app.main.forms import EditProfileForm, EmptyForm, PostForm, SearchForm
from app.models import User, Post, followers, post_likes
from app.translate import translate
from app import ai_improve
from app.embeddings import embed_to_json
from app.retrieval import find_similar_posts, find_similar_messages, \
    find_user_messages, find_for_you_posts, find_for_you_users
from app.main import bp


@bp.before_app_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.now(timezone.utc)
        db.session.commit()
    g.locale = str(get_locale())


@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    form = PostForm()
    if form.validate_on_submit():
        try:
            language = detect(form.post.data)
        except LangDetectException:
            language = ''
        post = Post(body=form.post.data, author=current_user,
                    language=language,
                    embedding=embed_to_json(form.post.data))
        db.session.add(post)
        db.session.commit()
        flash(_('Your post is now live!'))
        return redirect(url_for('main.index'))
    page = request.args.get('page', 1, type=int)
    posts = db.paginate(current_user.following_posts(), page=page,
                        per_page=current_app.config['POSTS_PER_PAGE'],
                        error_out=False)
    next_url = url_for('main.index', page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('main.index', page=posts.prev_num) \
        if posts.has_prev else None
    return render_template('index.html', title=_('Home'), form=form,
                           posts=posts.items, next_url=next_url,
                           prev_url=prev_url)


@bp.route('/explore')
@login_required
def explore():
    tab = request.args.get('tab', 'posts')
    per_page = current_app.config['POSTS_PER_PAGE']

    recommended_posts = []
    next_url = None
    prev_url = None
    recommended_users = []

    if tab == 'users':
        recommended_users = find_for_you_users(current_user, limit=10)
    else:
        page = request.args.get('page', 1, type=int)
        recommended_posts, total = find_for_you_posts(current_user, page=page, per_page=per_page)
        if page > 1:
            prev_url = url_for('main.explore', tab='posts', page=page - 1)
        if page * per_page < total:
            next_url = url_for('main.explore', tab='posts', page=page + 1)

    return render_template('for_you.html', title=_('For You'),
                           tab=tab,
                           posts=recommended_posts,
                           users=recommended_users,
                           next_url=next_url,
                           prev_url=prev_url)


@bp.route('/user/<username>')
@login_required
def user(username):
    user = db.first_or_404(sa.select(User).where(User.username == username))
    page = request.args.get('page', 1, type=int)
    query = user.posts.select().order_by(Post.timestamp.desc())
    posts = db.paginate(query, page=page,
                        per_page=current_app.config['POSTS_PER_PAGE'],
                        error_out=False)
    next_url = url_for('main.user', username=user.username,
                       page=posts.next_num) if posts.has_next else None
    prev_url = url_for('main.user', username=user.username,
                       page=posts.prev_num) if posts.has_prev else None
    form = EmptyForm()
    return render_template('user.html', user=user, posts=posts.items,
                           next_url=next_url, prev_url=prev_url, form=form)


@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash(_('Your changes have been saved.'))
        return redirect(url_for('main.edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', title=_('Edit Profile'),
                           form=form)


@bp.route('/follow/<username>', methods=['POST'])
@login_required
def follow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.username == username))
        if user is None:
            flash(_('User %(username)s not found.', username=username))
            return redirect(url_for('main.index'))
        if user == current_user:
            flash(_('You cannot follow yourself!'))
            return redirect(url_for('main.user', username=username))
        current_user.follow(user)
        db.session.commit()
        flash(_('You are following %(username)s!', username=username))
        return redirect(url_for('main.user', username=username))
    else:
        return redirect(url_for('main.index'))


@bp.route('/unfollow/<username>', methods=['POST'])
@login_required
def unfollow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.username == username))
        if user is None:
            flash(_('User %(username)s not found.', username=username))
            return redirect(url_for('main.index'))
        if user == current_user:
            flash(_('You cannot unfollow yourself!'))
            return redirect(url_for('main.user', username=username))
        current_user.unfollow(user)
        db.session.commit()
        flash(_('You are not following %(username)s.', username=username))
        return redirect(url_for('main.user', username=username))
    else:
        return redirect(url_for('main.index'))


@bp.route('/like/<int:post_id>', methods=['POST'])
@login_required
def like_post(post_id):
    post = db.get_or_404(Post, post_id)
    if post.is_liked_by(current_user):
        post.liked_by.remove(current_user)
        liked = False
    else:
        post.liked_by.add(current_user)
        liked = True
    db.session.commit()
    return {'liked': liked, 'count': post.like_count()}


@bp.route('/translate', methods=['POST'])
@login_required
def translate_text():
    data = request.get_json()
    return {'text': translate(data['text'],
                              data['source_language'],
                              data['dest_language'])}


@bp.route('/improve-post', methods=['POST'])
@login_required
def improve_post():
    data = request.get_json()
    text = (data or {}).get('text', '')
    if not text:
        return {'error': 'No text provided'}, 400
    try:
        return {'text': ai_improve.improve_post(text)}
    except Exception as e:
        return {'error': str(e)}, 500


_MESSAGE_KEYWORDS = [
    'message', 'messages', 'inbox', 'chat', 'chats', 'conversation',
    'conversations', 'dm', 'dms', 'direct message', 'direct messages',
    'what did i say', 'what did they say to me', 'what did he say',
    'what did she say', 'what did they say', 'what did someone say',
    'what did we talk about', 'what did we discuss', 'talked about',
    'talk about', 'discussed',
    'said to me', 'told me', 'sent me',
    'i sent', 'replied', 'reply from', 'texted', 'text from',
]
_MESSAGE_PATTERNS = [
    re.compile(r'\bwhat did .+ (say|tell|send|reply)\b'),
    re.compile(r'\bwhat did (we|you and i) (talk about|discuss)\b'),
    re.compile(r'\b(messages?|dms?|chats?|conversations?) (with|from|to) .+'),
    re.compile(r'\b(with|from|to) .+ (messages?|dms?|chats?|conversation)\b'),
]
_MESSAGE_PARTNER_PATTERNS = [
    re.compile(r'\bwhat did (?P<name>[a-z0-9_.-]+) (?:say|tell|send|reply)\b'),
    re.compile(r'\b(?:messages?|dms?|chats?|conversations?) (?:with|from|to) (?P<name>[a-z0-9_.-]+)\b'),
    re.compile(r'\b(?:with|from|to) (?P<name>[a-z0-9_.-]+) (?:messages?|dms?|chats?|conversation)\b'),
]
_MESSAGE_PARTNER_PRONOUNS = {
    'i', 'me', 'my', 'we', 'us', 'our', 'you', 'he', 'him', 'she', 'her',
    'they', 'them', 'someone', 'somebody',
}
_POST_KEYWORDS = [
    'post', 'people saying', 'what are people', 'what are users',
    'community', 'others saying', 'feed', 'trending', 'someone said',
    'users say', 'what is being said',
]


def _wants_message_context(message):
    lower = message.lower()
    keyword_hit = any(
        re.search(r'\b' + re.escape(kw) + r'\b', lower)
        for kw in _MESSAGE_KEYWORDS
    )
    return (
        keyword_hit or
        any(pattern.search(lower) for pattern in _MESSAGE_PATTERNS)
    )


def _trim_chat_history(history, max_messages=8):
    if not isinstance(history, list):
        return []
    trimmed = []
    for entry in history:
        if not isinstance(entry, dict):
            continue
        role = entry.get('role')
        content = entry.get('content')
        if role not in ('user', 'assistant') or not isinstance(content, str):
            continue
        content = content.strip()
        if content:
            trimmed.append({'role': role, 'content': content})
    return trimmed[-max_messages:]


def _extract_message_partner(message):
    lower = message.lower()
    for pattern in _MESSAGE_PARTNER_PATTERNS:
        match = pattern.search(lower)
        if match:
            name = match.group('name')
            if name not in _MESSAGE_PARTNER_PRONOUNS:
                return name
    return None


def _find_message_partner(name):
    if not name:
        return None
    return db.session.scalar(
        sa.select(User)
        .where(User.id != current_user.id)
        .where(sa.func.lower(User.username) == name.lower())
    )


@bp.route('/chat', methods=['POST'])
@login_required
def chat():
    data = request.get_json()
    message = (data or {}).get('message', '').strip()
    history = _trim_chat_history((data or {}).get('history', []))
    if not message:
        return {'error': 'No message provided'}, 400

    lower = message.lower()
    wants_messages = _wants_message_context(message)
    wants_posts = any(kw in lower for kw in _POST_KEYWORDS)

    post_context = find_similar_posts(message, k=5) if wants_posts else None
    message_context = None
    if wants_messages:
        partner_name = _extract_message_partner(message)
        partner = _find_message_partner(partner_name)
        if partner_name:
            message_context = find_user_messages(
                current_user.id,
                partner_id=partner.id,
                limit=20,
            ) if partner else []
        else:
            message_context = find_user_messages(current_user.id, limit=30)

    try:
        response = ai_improve.chat_response(
            message=message,
            history=history,
            username=current_user.username,
            post_context=post_context,
            message_context=message_context,
        )
        return {'response': response}
    except Exception as e:
        return {'error': str(e)}, 500


@bp.route('/search')
@login_required
def search():
    form = SearchForm(request.args)
    if not form.validate():
        return redirect(url_for('main.index'))

    q = form.q.data.strip()
    result_type = request.args.get('type', 'all')

    is_following = (
        sa.select(followers)
        .where(followers.c.follower_id == current_user.id)
        .where(followers.c.followed_id == User.id)
        .exists()
    )
    is_followed_by = (
        sa.select(followers)
        .where(followers.c.follower_id == User.id)
        .where(followers.c.followed_id == current_user.id)
        .exists()
    )
    tier = sa.case(
        (sa.and_(is_following, is_followed_by), 1),
        (sa.or_(is_following, is_followed_by), 2),
        else_=3
    )

    pattern = f'%{q}%'

    user_results = []
    if result_type in ('all', 'users'):
        user_results = db.session.scalars(
            sa.select(User)
            .where(User.id != current_user.id)
            .where(sa.or_(
                User.username.ilike(pattern),
                User.about_me.ilike(pattern)
            ))
            .order_by(tier, User.username)
        ).all()

    post_results = []
    if result_type in ('all', 'posts'):
        Author = so.aliased(User)
        author_is_following = (
            sa.select(followers)
            .where(followers.c.follower_id == current_user.id)
            .where(followers.c.followed_id == Author.id)
            .exists()
        )
        author_is_followed_by = (
            sa.select(followers)
            .where(followers.c.follower_id == Author.id)
            .where(followers.c.followed_id == current_user.id)
            .exists()
        )
        author_tier = sa.case(
            (sa.and_(author_is_following, author_is_followed_by), 1),
            (sa.or_(author_is_following, author_is_followed_by), 2),
            else_=3
        )
        post_results = db.session.scalars(
            sa.select(Post)
            .join(Author, Post.author)
            .where(Post.body.ilike(pattern))
            .order_by(author_tier, Post.timestamp.desc())
        ).all()

    return render_template('search.html', title=_('Search'),
                           q=q, result_type=result_type,
                           user_results=user_results,
                           post_results=post_results,
                           form=form)
