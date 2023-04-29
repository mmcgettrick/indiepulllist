from subscriptions import app, db
from subscriptions.forms import IssueOrderForm, SeriesSearchForm
from subscriptions.models import Issue, Series, Subscription, UserOrder
from collections import OrderedDict
from flask import flash, redirect, render_template, request, session, url_for
#from flask_login import current_user, LoginManager, login_manager, login_required
from flask_login import current_user, login_required
from datetime import date, datetime, timedelta

@app.route('/subscriptions')
@login_required
def subscriptions():
    subscriptions = Subscription.query.join(Series).filter(Subscription.user_id == current_user.get_id()).order_by(Series.name).all()
    return render_template('manage_my_subscriptions.html', subscriptions=subscriptions, title="My Subscriptions", back=request.referrer)

@app.route('/subscribe')
@app.route('/subscribe/')
@app.route('/subscribe/<id>')
@login_required
def subscribe(id=None):
    if(id==None):
        # error
        flash('Subscribe error!', category='danger')
        return redirect(url_for('series'))
    else:
        # todo check if series_id is valid
        subscription = Subscription(user_id=current_user.get_id(), series_id=id)
        db.session.add(subscription)

        # add all upcoming issues to user_orders
        #issues = Issue.query.filter_by(series_id=id).order_by(Issue.est_ship_date)
        #for issue in issues:
        #    order = UserOrder(user_id=current_user.get_id(), issue_id=issue.id, units=1)
        #    db.session.add(order)

        db.session.commit()
        # flash the result
        name = subscription.series.name
        flash(f'Subscribed to {name}', category='success')
        return redirect(url_for('subscriptions'))


@app.route('/unsubscribe')
@app.route('/unsubscribe/<id>')
@login_required
def unsubscribe(id=None):
    if(id==None):
        # error
        flash('Unsubscribe error!', category='danger')
        return redirect(url_for('subscriptions'))
    else:
        # check if series_id is valid
        subscription = Subscription.query.filter_by(user_id=current_user.get_id(), series_id=id).first()
        name = subscription.series.name
        db.session.delete(subscription)
        db.session.commit()
        # save it
        flash(f'Unsubscribed from {name}', category='success')
        return redirect(url_for('subscriptions'))


@app.route('/series')
@app.route('/series/<id>')
@login_required
def series(id=None):
    if(id==None):
        # Only list series with upcoming issues
        cutoff = datetime.now() - timedelta(days=30)
        series_query = Series.query.join(Issue.series).filter(Issue.est_ship_date > cutoff)
        form = SeriesSearchForm(request.args)
        # publishers
        if form.publishers.data:
            publisher_id = form.publishers.data.id
            series_query = series_query.filter(Series.publisher_id==publisher_id)
        # search term
        if form.search.data:
            series_query = series_query.filter(Issue.title.ilike(f"%{form.search.data}%"))
        # remove series where already subscribed
        series_query = series_query.outerjoin(Subscription).filter(Subscription.user_id == None)
        # order by name and return all matches
        #print(series_query)
        series = series_query.order_by(Series.name).all()

        return render_template('series.html', form=form, series=series, title="Series", back=request.referrer)
    else:
        # GET: pepare series and issue information
        today = date.today()
        series = Series.query.get(id)
        issues = Issue.query.filter_by(series_id=id).filter(Issue.est_ship_date > datetime.now()).order_by(Issue.est_ship_date)
        #issues = Issue.query.filter_by(series_id=id).order_by(Issue.est_ship_date)
        form = None #IssueOrderForm()
        # if authenticated add subscription and order info
        smap = {}
        # Get all issue / order pairs
        #issues = {i:None for i in issues}
        issues = OrderedDict()
        for issue, user_order in db.session.query(Issue, UserOrder).outerjoin(UserOrder, Issue.item_code==UserOrder.issue_id).filter(Issue.series_id==id).filter(Issue.est_ship_date > today).order_by(Issue.est_ship_date, Issue.title).all():
            if user_order==None:
                issues[issue] = None
            else:
                issues[issue] = user_order
        if current_user.is_authenticated:
            # subscriptions
            subscriptions = Subscription.query.filter_by(user_id=current_user.get_id())
            smap = {s.series.id:True for s in subscriptions}
            # orders
            form = IssueOrderForm(user_id=current_user.id)
        return render_template('series_detail.html', series=series, smap=smap, issues=issues, today=today, form=form, back=request.referrer)
