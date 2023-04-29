from subscriptions import app, db
from subscriptions.email import confirm_token, send_confirmation, send_fcbd2021_confirmation
from subscriptions.forms import ChangePasswordForm, LoginForm, ProfileForm, RegisterForm, UpdateInventoryForm
from subscriptions.models import Discount, Issue, ShippingMethod, SubscriptionType, ShoppingCart, User, UserProfile
from subscriptions.utils import calculate_items_in_cart
from flask import flash, jsonify, redirect, render_template, request, session, url_for
from flask_login import AnonymousUserMixin, current_user, LoginManager, login_required, login_user, logout_user
from functools import wraps
from sqlalchemy import create_engine, func
from uuid import uuid4
from werkzeug.security import check_password_hash, generate_password_hash
import boto3
import json
import hashlib


class AnonymousUser(AnonymousUserMixin):

    def get_id(self):
        if 'anaonymous_user_id' not in session:
            session['anaonymous_user_id'] = str(uuid4())
        return session['anaonymous_user_id']

# Setup LoginManager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.anonymous_user = AnonymousUser
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

# Custom decorator to check for admin status
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = User.query.filter_by(id=current_user.get_id()).first()
        if user.admin is False:
            flash('Requires admin access!','danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# determine if email (case insensitive) exists in database
def user_exists(email):
    user = User.query.filter(func.lower(User.email)==email.lower()).first()
    if user:
        return True
    else:
        return False

# Handle 404s
@app.errorhandler(404)
def page_not_found(error):
    return render_template('page_not_found.html'), 404

# Routes
@app.route('/')
def index():
    #flash('Use code GRAND20 at checkout for 20% off your order!','success')
    return render_template("index.html")


@app.route('/change_password', methods=['GET','POST'])
@login_required
def change_password():
    form = ChangePasswordForm(request.form)
    if form.validate_on_submit():
        # validate current password
        user = User.query.filter_by(id=current_user.get_id()).first()
        if user:
            if check_password_hash(user.password, form.current_password.data):
                # change the password
                print(f"Old password: {user.password}")
                user.password = generate_password_hash(form.new_password.data)
                print(f"New password: {user.password}")
                # update database
                db.session.commit()
                # Flash success and redirect
                flash('Password changed!','success')
                redirect(url_for('index'))
            else:
                # current password doesn't match
                flash('Current password does not match your current password!','danger')
                return render_template('change_password.html', form=form)
        # user doesn't exist - should not happen!!!
    return render_template('change_password.html', form=form)


@app.route('/confirm/<token>')
def confirm_email(token):
    try:
        email = confirm_token(token)
        user = User.query.filter_by(email=email).first_or_404()
        if user.verified:
            flash('Account already confirmed. Please login.', 'success')
        else:
            user.verified = True
            db.session.add(user)
            db.session.commit()
            flash('You have confirmed your account. Thanks!', 'success')
            return redirect(url_for('login'))
    except Exception as e:
        print(e)
        flash('The confirmation link is invalid or has expired.', 'danger')
        return redirect(url_for('index'))


@app.route('/login', methods=['GET','POST'])
def login():
    form = LoginForm(request.form)
    if form.validate_on_submit():
        # capture anonymous user id
        anonymous_user_id = current_user.get_id()
        # lookup the user by email address
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            if check_password_hash(user.password, form.password.data):
                login_user(user)
                # convert any anonymous cart currently in progress
                if anonymous_user_id != current_user.get_id():
                    cart = ShoppingCart.query.filter_by(user_id=anonymous_user_id).all()
                    for c in cart:
                        # what if such a record already exists?
                        exists = ShoppingCart.query.filter_by(user_id=current_user.get_id(), issue_id=c.issue_id).first()
                        if exists:
                            print("Ignoring conflict on merge")
                            #exists.units = exists.units + c.units
                        else:
                            c.user_id = current_user.get_id()
                    db.session.commit()
                # update cart count in session
                session['items_in_cart'] = calculate_items_in_cart(ShoppingCart.query.filter_by(user_id=current_user.get_id()).all())
                # apply coupon code if exists
                discount = Discount.query.filter(Discount.owner_email==user.email).first()
                if discount:
                    session['coupon_code'] = discount.code
                    if len(discount.code) > 0:
                        flash(f'Applied Coupon Code: {discount.code}','success')
                # continue
                flash('Logged in successfully.', category="success")
                return redirect(url_for('index'))
        flash('Login error!', category="danger")
        return redirect(url_for('index'))
    return render_template("login.html", form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    flash('Logged out successfully.', category="success")
    return redirect(url_for('index'))


@app.route('/profile', methods=['GET','POST'])
@login_required
def profile():
    form = ProfileForm(request.form)
    if form.validate_on_submit():
        shipping_frequency = int(request.form['shipping_frequency'])
        shipping_method_id = int(request.form['shipping_method'])
        default_subscription_type_id = int(request.form['default_subscription_type'])
        #update database
        profile = UserProfile.query.filter_by(user_id=current_user.id).first()
        profile.shipping_frequency = shipping_frequency
        profile.shipping_method_id = shipping_method_id
        profile.default_subscription_type_id = default_subscription_type_id
        db.session.commit()
    methods = ShippingMethod.query.all()
    types = SubscriptionType.query.all()
    profile = UserProfile.query.filter_by(user_id=current_user.id).first()
    return render_template('profile.html', profile=profile, methods=methods, types=types, form=form)


@app.route('/register', methods=['GET','POST'])
def register():
    form = RegisterForm(request.form)
    if form.validate_on_submit():
        email=form.email.data
        password=generate_password_hash(form.password.data)
        # does user already exist?
        if user_exists(email):
            flash('That email address is already reistered! Please login or try another email address.', category='warning')
            return render_template('register.html', form=form)
        else:
            id = str(uuid4())
            user = User(id=id, email=email, password=password)
            user_profile = UserProfile(user_id=id, shipping_frequency=1, shipping_method_id=3, default_subscription_type_id=1, discount_id=1)
            db.session.add(user)
            db.session.add(user_profile)
            db.session.commit()
            # todo send validation email
            send_confirmation(email)
            flash('Thanks for registering! Please check for email confirmation.', category='success')
            return redirect(url_for('login'))
    return render_template('register.html', form=form)


@app.route('/ebay_account_deletion_endpoint', methods=['GET','POST'])
def ebayAccountDeletionEndpoint():
    if request.method=='GET':
        challenge_code = request.args.get('challenge_code').encode('utf-8')
        #challenge_response = challenge_code
        verification_token = 'IndiePullListVerificationTokenOfDoom'.encode('utf-8')
        endpoint = 'https://indiepulllist.com/ebay_account_deletion_endpoint'.encode('utf-8')
        m = hashlib.sha256(challenge_code + verification_token + endpoint)
        #m = hashlib.sha256(challenge_code + endpoint)
        challenge_response = m.hexdigest()
        data = {'challengeResponse':challenge_response}
        return jsonify(data)
    else:
        return '', 200

# TEMPORARY FOR FCBD2021
#@app.route('/fcbd2021order', methods=['POST'])
#def fcbd2021order():
#    issues = [
#        ['APR210042','10 TON OF FUN SAMPLER'],
#        ['APR210037','2000 AD PRESENTS ALL STAR JUDGE DREDD #1'],
#        ['APR210026','ADV OF BAILEY SCHOOL KIDS'],
#        ['APR210025','ALLERGIC'],
#        ['APR210019','AVATAR LAST AIRBENDER LEGEND OF KORRA'],
#        ['APR210017','BLACK CALEXIT FCBD SPECIAL'],
#        ['APR210010','BLADE RUNNER ONESHOT'],
#        ['APR210030','BOUNTIFUL GARDEN #1'],
#        ['APR210032','DUNGEON IS BACK'],
#        ['APR210003','ENTER THE SLAUGHTER'],
#        ['APR210039','FUNGIRL TALES OF A GROWN UP NOTHING'],
#        ['APR210040','GLOOMHAVEN HOLE IN THE WALL ONESHOT'],
#        ['APR210005','INVESTIGATORS ANTS IN PANTS SNEAK PEEK'],
#        ['APR210018','JUST BEYOND MONSTROSITY #1'],
#        ['APR210050','KYLES LITTLE SISTER'],
#        ['APR210007','LADY MECHANIKA'],
#        ['APR210048','LAST KIDS ON EARTH'],
#        ['APR210043','LIFE IS STRANGE ONESHOT'],
#        ['APR210008','MARVEL GOLD AVENGERS HULK #1'],
#        ['APR210041','ON TYRANNY PREVIEW'],
#        ['APR210034','ONI PRESS SUMMER CELEBRATION'],
#        ['APR210023','RED ROOM FCBD EDITION'],
#        ['APR210029','RENT A REALLY SHY GIRLFRIEND PREVIEW'],
#        ['APR210016','RESISTANCE UPRISING #1'],
#        ['APR210035','SCHOOL FOR EXTRATERRESTRIAL GIRLS'],
#        ['APR210036','SMURFS TALES'],
#        ['APR210051','SOLO LEVELING'],
#        ['APR210027','SONIC THE HEDGEHOG 30TH ANNIVERSARY'],
#        ['APR210013','SPACE PIRATE CAPTAIN HARLOCK'],
#        ['APR210006','STAR WARS HIGH REPUBLIC ADVENTURES'],
#        ['APR210049','STAR WARS HIGH REPUBLIC BALANCE & GUARDIANS'],
#        ['APR210028','STRAY DOGS'],
#        ['APR210044','STREET FIGHTER BACK TO SCHOOL SPECIAL #1'],
#        ['APR210021','THE BOYS HEROGASM #1'],
#        ['APR210014','TRESE'],
#        ['APR210046','UNFINISHED CORNER'],
#        ['APR210045','VALIANT UPRISING'],
#        ['APR210022','VAMPIRELLA #1'],
#        ['APR210001','WE LIVE LAST DAYS'],
#        ['APR210038','WHITE ASH SEASON 2 #0'],
#        ['APR210009','WHO SPARKED MONTGOMERY BUS BOYCOTT'],
#        ['APR210012','ZOM 100 BUCKET LIST OF THE DEAD']
#    ]
#    order = request.form.to_dict()
#    filtered_issues = [i for i in issues if i[0] in order]
#    # email order confirmation
#    send_fcbd2021_confirmation(order, filtered_issues)#

#    return render_template('fcbd2021order.html', order=order, issues=filtered_issues)#
#

#@app.route('/fcbd2021', methods=['GET'])
#def fcbd2021():
#    issues = [
#        ['APR210042','10 TON OF FUN SAMPLER'],
#        ['APR210037','2000 AD PRESENTS ALL STAR JUDGE DREDD #1'],
#        ['APR210026','ADV OF BAILEY SCHOOL KIDS'],
#        ['APR210025','ALLERGIC'],
#        ['APR210019','AVATAR LAST AIRBENDER LEGEND OF KORRA'],
#        ['APR210017','BLACK CALEXIT FCBD SPECIAL'],
#        ['APR210010','BLADE RUNNER ONESHOT'],
#        ['APR210030','BOUNTIFUL GARDEN #1'],
#        ['APR210032','DUNGEON IS BACK'],
#        ['APR210003','ENTER THE SLAUGHTER'],
#        ['APR210039','FUNGIRL TALES OF A GROWN UP NOTHING'],
#        ['APR210040','GLOOMHAVEN HOLE IN THE WALL ONESHOT'],
#        ['APR210005','INVESTIGATORS ANTS IN PANTS SNEAK PEEK'],
#        ['APR210018','JUST BEYOND MONSTROSITY #1'],
#        ['APR210050','KYLES LITTLE SISTER'],
#        ['APR210007','LADY MECHANIKA'],
#        ['APR210048','LAST KIDS ON EARTH'],
#        ['APR210043','LIFE IS STRANGE ONESHOT'],
#        ['APR210008','MARVEL GOLD AVENGERS HULK #1'],
#        ['APR210041','ON TYRANNY PREVIEW'],
#        ['APR210034','ONI PRESS SUMMER CELEBRATION'],
#        ['APR210023','RED ROOM FCBD EDITION'],
#        ['APR210029','RENT A REALLY SHY GIRLFRIEND PREVIEW'],
#        ['APR210016','RESISTANCE UPRISING #1'],
#        ['APR210035','SCHOOL FOR EXTRATERRESTRIAL GIRLS'],
#        ['APR210036','SMURFS TALES'],
#        ['APR210051','SOLO LEVELING'],
#        ['APR210027','SONIC THE HEDGEHOG 30TH ANNIVERSARY'],
#        ['APR210013','SPACE PIRATE CAPTAIN HARLOCK'],
#        ['APR210006','STAR WARS HIGH REPUBLIC ADVENTURES'],
#        ['APR210049','STAR WARS HIGH REPUBLIC BALANCE & GUARDIANS'],
#        ['APR210028','STRAY DOGS'],
#        ['APR210044','STREET FIGHTER BACK TO SCHOOL SPECIAL #1'],
#        ['APR210021','THE BOYS HEROGASM #1'],
#        ['APR210014','TRESE'],
#        ['APR210046','UNFINISHED CORNER'],
#        ['APR210045','VALIANT UPRISING'],
#        ['APR210022','VAMPIRELLA #1'],
#        ['APR210001','WE LIVE LAST DAYS'],
#        ['APR210038','WHITE ASH SEASON 2 #0'],
#        ['APR210009','WHO SPARKED MONTGOMERY BUS BOYCOTT'],
#        ['APR210012','ZOM 100 BUCKET LIST OF THE DEAD']
#    ]
#    return render_template('fcbd2021.html', title='Free Comic Book Day 2021', issues=issues)

# TEMPORARY FOR TESTING
@app.route('/issues', methods=['GET','POST'])
def issues():
    if request.method=='POST':
        print(request.form)
        form = IssueOrderForm(request.form)
        print('UserID: %d' % form.user_id.data)
        print(form.orders.data)
        return redirect(url_for('index'))
    # Get all issue / order pairs
    issues = OrderedDict()
    for issue, user_order in db.session.query(Issue, UserOrder).outerjoin(UserOrder, Issue.id==UserOrder.issue_id).order_by(Issue.est_ship_date, Issue.title).all():
        if user_order==None:
            issues[issue] = None
        else:
            issues[issue] = user_order
    form = IssueOrderForm(user_id=current_user.id)
    return render_template('issues.html', issues=issues, form=form)

@app.route('/users')
@admin_required
@login_required
def users():
    users = User.query.all()
    return str(users)
