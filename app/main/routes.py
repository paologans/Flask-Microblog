from datetime import datetime, timezone
from flask import render_template, flash, redirect, url_for, request, g, \
    current_app
from flask_login import current_user, login_required
from flask_babel import _, get_locale
import sqlalchemy as sa
import sqlalchemy.orm as so
from langdetect import detect, LangDetectException
from app import db
from app.main.forms import EditProfileForm, EmptyForm, PostForm, SearchForm
from app.models import User, Post, followers
from app.translate import translate
from app import ai_improve
from app.embeddings import embed_to_json
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
    page = request.args.get('page', 1, type=int)
    query = sa.select(Post).order_by(Post.timestamp.desc())
    posts = db.paginate(query, page=page,
                        per_page=current_app.config['POSTS_PER_PAGE'],
                        error_out=False)
    next_url = url_for('main.explore', page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('main.explore', page=posts.prev_num) \
        if posts.has_prev else None
    return render_template('index.html', title=_('Explore'),
                           posts=posts.items, next_url=next_url,
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
