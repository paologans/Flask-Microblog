from datetime import datetime
from flask import render_template, redirect, url_for, request, flash
from flask_login import current_user, login_required
from app import db
from app.messages import bp
from app.messages.forms import MessageForm
from app.models import User, Message


@bp.route('/messages')
@bp.route('/messages/<username>', methods=['GET','POST'])
@login_required
def inbox(username=None):

    current_user.last_message_read_time = datetime.utcnow()
    db.session.commit()

    sent_to = db.session.query(Message.recipient_id).filter_by(
        sender_id=current_user.id)
    received_from = db.session.query(Message.sender_id).filter_by(
        recipient_id=current_user.id)

    partner_ids = sent_to.union(received_from).all()
    partner_ids = [row[0] for row in partner_ids]

    partners = []
    for pid in partner_ids:
        user = User.query.get(pid)
        if user:

            latest = Message.query.filter(
                db.or_(
                    db.and_(Message.sender_id == current_user.id,
                            Message.recipient_id == pid),
                    db.and_(Message.sender_id == pid,
                            Message.recipient_id == current_user.id)
                )
            ).order_by(Message.timestamp.desc()).first()
            partners.append((user, latest))


    partners.sort(key=lambda x: x[1].timestamp, reverse=True)

    active_user = None
    messages = []
    form = None
    has_more = False

    if username:
        active_user = User.query.filter_by(username=username).first_or_404()
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
        msgs = Message.query.filter(
            db.or_(
                db.and_(Message.sender_id == current_user.id,
                        Message.recipient_id == active_user.id),
                db.and_(Message.sender_id == active_user.id,
                        Message.recipient_id == current_user.id)
            )
        ).order_by(Message.timestamp.desc()).limit(PAGE).all()
        msgs.reverse()
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
    partner = User.query.filter_by(username=username).first_or_404()
    before_id = request.args.get('before_id', type=int)
    limit = 20

    query = Message.query.filter(
        db.or_(
            db.and_(Message.sender_id == current_user.id,
                    Message.recipient_id == partner.id),
            db.and_(Message.sender_id == partner.id,
                    Message.recipient_id == current_user.id)
        )
    )
    if before_id:
        query = query.filter(Message.id < before_id)

    msgs = query.order_by(Message.timestamp.desc()).limit(limit).all()
    msgs.reverse()

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