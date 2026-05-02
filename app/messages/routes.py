from datetime import datetime, timezone
from flask import render_template, redirect, url_for, request, flash
from flask_login import current_user, login_required
import sqlalchemy as sa
from app import db
from app.messages import bp
from app.messages.forms import MessageForm
from app.models import User, Message


@bp.route('/messages')
@bp.route('/messages/<username>', methods=['GET', 'POST'])
@login_required
def inbox(username=None):
    current_user.last_message_read_time = datetime.now(timezone.utc)
    db.session.commit()

    sent_to = sa.select(Message.recipient_id).where(
        Message.sender_id == current_user.id)
    received_from = sa.select(Message.sender_id).where(
        Message.recipient_id == current_user.id)

    partner_ids = db.session.scalars(sent_to.union(received_from)).all()

    partners = []
    for pid in partner_ids:
        user = db.session.get(User, pid)
        if user:
            latest = db.session.scalar(
                sa.select(Message).where(
                    sa.or_(
                        sa.and_(Message.sender_id == current_user.id,
                                Message.recipient_id == pid),
                        sa.and_(Message.sender_id == pid,
                                Message.recipient_id == current_user.id)
                    )
                ).order_by(Message.timestamp.desc())
            )
            partners.append((user, latest))

    partners.sort(key=lambda x: x[1].timestamp, reverse=True)

    active_user = None
    messages = []
    form = None
    has_more = False

    if username:
        active_user = db.first_or_404(sa.select(User).where(User.username == username))
        form = MessageForm()

        if form.validate_on_submit():
            msg = Message(sender=current_user,
                          recipient=active_user,
                          body=form.body.data)
            db.session.add(msg)
            db.session.commit()
            flash('Message sent.')
            return redirect(url_for('messages.inbox', username=username))

        PAGE = 20
        msgs = db.session.scalars(
            sa.select(Message).where(
                sa.or_(
                    sa.and_(Message.sender_id == current_user.id,
                            Message.recipient_id == active_user.id),
                    sa.and_(Message.sender_id == active_user.id,
                            Message.recipient_id == current_user.id)
                )
            ).order_by(Message.timestamp.desc()).limit(PAGE)
        ).all()
        msgs = list(reversed(msgs))
        messages = msgs
        has_more = len(msgs) == PAGE

    return render_template('messages/inbox.html',
                           partners=partners,
                           active_user=active_user,
                           messages=messages,
                           has_more=has_more,
                           form=form)


@bp.route('/messages/<username>/history')
@login_required
def message_history(username):
    partner = db.first_or_404(sa.select(User).where(User.username == username))
    before_id = request.args.get('before_id', type=int)
    limit = 20

    query = sa.select(Message).where(
        sa.or_(
            sa.and_(Message.sender_id == current_user.id,
                    Message.recipient_id == partner.id),
            sa.and_(Message.sender_id == partner.id,
                    Message.recipient_id == current_user.id)
        )
    )
    if before_id:
        query = query.where(Message.id < before_id)

    msgs = db.session.scalars(
        query.order_by(Message.timestamp.desc()).limit(limit)
    ).all()
    msgs = list(reversed(msgs))

    return {
        'messages': [{
            'id': m.id,
            'body': m.body,
            'is_mine': m.sender_id == current_user.id,
            'timestamp_iso': m.timestamp.isoformat(),
            'avatar': partner.avatar(32) if m.sender_id == partner.id else None,
        } for m in msgs],
        'has_more': len(msgs) == limit
    }