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

        messages = Message.query.filter(
            db.or_(
                db.and_(Message.sender_id == current_user.id,
                        Message.recipient_id == active_user.id),
                db.and_(Message.sender_id == active_user.id,
                        Message.recipient_id == current_user.id)
            )
        ).order_by(Message.timestamp.asc()).all()

    return render_template('messages/inbox.html',
                           partners=partners,
                           active_user=active_user,
                           messages=messages,
                           form=form)