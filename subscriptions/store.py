import boto3
from subscriptions import app, db
from subscriptions.email import send_invoice
from subscriptions.forms import AddToShoppingCartForm, InventoryItemForm, MangaSearchForm, SearchInventoryForm, ShoppingCartItemForm, StoreSearchForm, UpdateCouponCodeForm, UpdateInventoryForm, UpdateShippingMethodForm
from subscriptions.models import Discount, EmailPreferences, Inventory, InventorySale, Issue, Order, OrderItem, Publisher, Series, ShippingMethod, ShoppingCart, UserProfile
from subscriptions.routes import admin_required
from subscriptions.utils import calculate_discount, calculate_items_in_cart, calculate_subtotal, calculate_shipping, convert_cart_to_order, group_inventory, max_units_available, send_new_order_sqs_message
from datetime import datetime, timedelta
from flask import flash, redirect, render_template, request, session, url_for
from flask_login import current_user, LoginManager, login_manager, login_required
from paypalcheckoutsdk.orders import OrdersGetRequest
from sqlalchemy import desc, func
from subscriptions.paypal import get_paypal_client


@app.route('/apply_coupon_code', methods=['POST'])
def apply_coupon_code():
    form = UpdateCouponCodeForm(request.form)
    if form.validate_on_submit():
        # validate the coupon code!
        coupon_code = form.coupon_code.data.strip()
        discount = Discount.query.filter(Discount.code==coupon_code).first()
        if discount:
            if discount.disabled:
                flash(f'Failed to apply disabled coupon code: {coupon_code}!','danger')
            #elif discount.owner_email:
                # check if owner_email matches login user
                # print ''
            else:
                session['coupon_code'] = coupon_code
                if len(coupon_code) > 0:
                    flash(f'Applied Coupon Code: {coupon_code}!','success')
        else:
            flash(f'Error with Coupon Code: {coupon_code}!','danger')
        return redirect(url_for('shopping_cart'))
    return redirect(url_for('shopping_cart'))


@app.route('/orders/<id>')
def order(id=None):
    orders = [Order.query.filter_by(user_id=current_user.get_id()).filter_by(paypal_order_id=id).first()]
    return render_template('orders.html', orders=orders, title='Order Detail')


@app.route('/orders')
@login_required
def orders():
    orders = Order.query.filter_by(user_id=current_user.get_id()).order_by(desc(Order.date)).all()
    return render_template('orders.html', orders=orders, title='Order History')


@app.route("/manga", methods=['GET'])
def manga():
    # Default discount
    discount = Discount.query.filter_by(name='Store Discount').first()
    # Override with user discount
    user_profile = UserProfile.query.filter_by(user_id=current_user.get_id()).first()
    if user_profile:
        discount = user_profile.discount

    session['items_in_cart'] = calculate_items_in_cart(ShoppingCart.query.filter_by(user_id=current_user.get_id()).all())

    # search form
    search_form = MangaSearchForm(request.args)
    inventory_query = Inventory.query.filter(Inventory.units > 0).filter(Inventory.hidden == False).join(Publisher).filter(Publisher.name!='DC Comics').filter(Publisher.name!='Marvel Comics').filter(Publisher.manga==True)
    if search_form.search.data:
        inventory_query = inventory_query.filter(Inventory.title.ilike(f"%{search_form.search.data}%"))
    # limit publishers
    if search_form.publishers.data:
        publisher_id = search_form.publishers.data.id
        inventory_query = inventory_query.filter(Inventory.publisher_id==publisher_id)
    if search_form.on_sale.data:
        inventory_query = inventory_query.join(InventorySale).filter(InventorySale.sale_percentage > 0.00)
    # set sort
    if search_form.sort_by.data:
        sort_directive = search_form.sort_by.data
        # Newest > Title
        if sort_directive=='newest':
            inventory_query = inventory_query.order_by(desc(Inventory.release_date), Inventory.title)
        # Title > Newest
        elif sort_directive=='title_az':
            inventory_query = inventory_query.order_by(Inventory.title, desc(Inventory.release_date))
        # Publisher > Newest > Title
        elif sort_directive=='publisher_newest':
            inventory_query = inventory_query.order_by(Publisher.name, desc(Inventory.release_date), Inventory.title)
        # Publisher > Title > Newest
        elif sort_directive=='publisher_az':
            inventory_query = inventory_query.order_by(Publisher.name, Inventory.title, desc(Inventory.release_date))
        else:
            # default is by Newest > Title
            inventory_query = inventory_query.order_by(desc(Inventory.release_date), Inventory.title)
    else:
        # by default sort newest, then by title A-Z
        inventory_query = inventory_query.order_by(desc(Inventory.release_date), Inventory.title)
    # collect!
    inventory = inventory_query.all()
    # GROUP THE RESULTS
    grouped_inventory = group_inventory(inventory, search_form.sort_by.data)
    return render_template('manga.html', discount=discount, grouped_inventory=grouped_inventory, inventory=inventory, search_form=search_form, title='Manga')


@app.route('/manga/<id>')
def manga_detail(id=None):
    # Default discount
    discount = Discount.query.filter_by(name='Store Discount').first()
    # Override with user discount
    user_profile = UserProfile.query.filter_by(user_id=current_user.get_id()).first()
    if user_profile:
        discount = user_profile.discount
    session['items_in_cart'] = calculate_items_in_cart(ShoppingCart.query.filter_by(user_id=current_user.get_id()).all())
    if id:
        # display store detail for one item
        inventory = Inventory.query.filter(Inventory.issue_id == id, Inventory.units > 0).first()
        if inventory:
            form = AddToShoppingCartForm(issue_id=inventory.issue_id, units=1)
            return render_template('store_detail.html', discount=discount, form=form, inventory=inventory, back=request.referrer)
        else:
            flash('Item is out of stock!','danger')
            return redirect(url_for('manga'))
    else:
        render_template('page_not_found.html'), 404


@app.route("/store", methods=['GET'])
def store():
    return redirect(url_for('comics'))

@app.route("/comics", methods=['GET'])
def comics():
    #search = request.args.get('search')
    #publisher = request.args.get('publisher')
    #sort_by = request.args.get('sort_by')
    #print(f"{search},{publisher},{sort_by}")
    # Default discount
    discount = Discount.query.filter_by(name='Store Discount').first()
    # Override with user discount
    user_profile = UserProfile.query.filter_by(user_id=current_user.get_id()).first()
    if user_profile:
        discount = user_profile.discount

    session['items_in_cart'] = calculate_items_in_cart(ShoppingCart.query.filter_by(user_id=current_user.get_id()).all())
    # search form
    search_form = StoreSearchForm(request.args)
    # display all "new' items (last 4 weeks)
    #cutoff = datetime.now() - timedelta(days=27)
    #inventory_query = Inventory.query.filter(Inventory.units > 0).filter(Inventory.hidden == False).filter(Inventory.release_date > cutoff).join(Inventory.issue)
    inventory_query = Inventory.query.filter(Inventory.units > 0).filter(Inventory.hidden == False).join(Publisher).filter(Publisher.name!='DC Comics').filter(Publisher.name!='Marvel Comics').filter(Publisher.comics==True)
    if search_form.search.data:
        inventory_query = inventory_query.filter(Inventory.title.ilike(f"%{search_form.search.data}%"))
    # limit publishers
    if search_form.publishers.data:
        publisher_id = search_form.publishers.data.id
        inventory_query = inventory_query.filter(Inventory.publisher_id==publisher_id)
    if search_form.on_sale.data:
        inventory_query = inventory_query.join(InventorySale).filter(InventorySale.sale_percentage > 0.00)
    # set sort
    if search_form.sort_by.data:
        sort_directive = search_form.sort_by.data
        # Newest > Title
        if sort_directive=='newest':
            inventory_query = inventory_query.order_by(desc(Inventory.release_date), Inventory.title)
        # Title > Newest
        elif sort_directive=='title_az':
            inventory_query = inventory_query.order_by(Inventory.title, desc(Inventory.release_date))
        # Publisher > Newest > Title
        elif sort_directive=='publisher_newest':
            inventory_query = inventory_query.order_by(Publisher.name, desc(Inventory.release_date), Inventory.title)
        # Publisher > Title > Newest
        elif sort_directive=='publisher_az':
            inventory_query = inventory_query.order_by(Publisher.name, Inventory.title, desc(Inventory.release_date))
        else:
            # default is by Newest > Title
            inventory_query = inventory_query.order_by(desc(Inventory.release_date), Inventory.title)
    else:
        # by default sort newest, then by title A-Z
        inventory_query = inventory_query.order_by(desc(Inventory.release_date), Inventory.title)
    # collect!
    inventory = inventory_query.all()
    # GROUP THE RESULTS
    grouped_inventory = group_inventory(inventory, search_form.sort_by.data)
    return render_template('store2.html', discount=discount, grouped_inventory=grouped_inventory, inventory=inventory, search_form=search_form, title='Comics')


@app.route('/store/<id>')
def store_detail(id=None):
    return redirect(url_for('comics')+f'/{id}')

@app.route('/comics/<id>')
def comics_detail(id=None):
    # Default discount
    discount = Discount.query.filter_by(name='Store Discount').first()
    # Override with user discount
    user_profile = UserProfile.query.filter_by(user_id=current_user.get_id()).first()
    if user_profile:
        discount = user_profile.discount
    session['items_in_cart'] = calculate_items_in_cart(ShoppingCart.query.filter_by(user_id=current_user.get_id()).all())
    if id:
        # display store detail for one item
        inventory = Inventory.query.filter(Inventory.issue_id == id, Inventory.units > 0).first()
        if inventory:
            form = AddToShoppingCartForm(issue_id=inventory.issue_id, units=1)
            return render_template('store_detail.html', discount=discount, form=form, inventory=inventory, back=request.referrer)
        else:
            flash('Item is out of stock!','danger')
            return redirect(url_for('store'))
    else:
        render_template('page_not_found.html'), 404


@app.route('/shopping_cart', methods=['GET','POST'])
def shopping_cart():
    # load default discount code
    discount_code = Discount.query.filter(Discount.code=='').first()
    # update if coupon_code is valid
    if 'coupon_code' in session:
        coupon_code = session['coupon_code']
        discount_coupon_code = Discount.query.filter(Discount.code==coupon_code).first()
        if discount_coupon_code:
            discount_code = discount_coupon_code
    shipping_method = ShippingMethod.query.filter_by(name='USPS Media Mail').first()
    methods = ShippingMethod.query.all()
    # populate the cart
    cart = ShoppingCart.query.filter_by(user_id=current_user.get_id()).join(Inventory).order_by(Inventory.title).all()
    subtotal = calculate_subtotal(cart)
    discount = calculate_discount(cart, discount_code)
    shipping = calculate_shipping(cart, shipping_method, discount_code)
    total = subtotal - discount + shipping
    # load inventory and build lookup map
    inventory = Inventory.query.filter(Inventory.hidden == False).all()
    inventory_units = { i.issue_id:i.units for i in inventory }
    # build forms
    forms = {item.issue_id:ShoppingCartItemForm(obj=item) for item in cart}
    shipping_method_form = UpdateShippingMethodForm(obj=shipping_method)
    coupon_code_form = UpdateCouponCodeForm()
    # set session values
    session['items_in_cart'] = calculate_items_in_cart(ShoppingCart.query.filter_by(user_id=current_user.get_id()).all())
    return render_template('cart2.html', config=app.config, forms=forms, coupon_code_form=coupon_code_form, discount=discount, discount_code=discount_code, inventory=inventory_units, methods=methods, shipping_method=shipping_method, shipping_method_form=shipping_method_form, shopping_cart=cart, subtotal=subtotal, shipping=shipping, total=total, title='Shopping Cart')


@app.route('/add_to_shopping_cart', methods=['POST'])
def add_to_shopping_cart():
    form = AddToShoppingCartForm(request.form)
    if form.validate_on_submit():
        issue_id = form.issue_id.data
        units = int(form.units.data)
        # try to get it
        cart = ShoppingCart.query.filter_by(user_id=current_user.get_id(), issue_id=issue_id).first()
        if cart:
            cart.units = cart.units + units
        else:
            cart = ShoppingCart(user_id=current_user.get_id(), issue_id=issue_id, units=units)
            db.session.add(cart)
        db.session.commit()
        session['items_in_cart'] = calculate_items_in_cart(ShoppingCart.query.filter_by(user_id=current_user.get_id()).all())
        flash('Item added to cart!','success')
        return redirect(f"{url_for('store')}/{issue_id}")
    else:
        flash('Add To Shopping Cart Failed','danger')
        return redirect(f"{url_for('store')}/{issue_id}")


@app.route('/update_shopping_cart', methods=['POST'])
def update_shopping_cart():
    form = ShoppingCartItemForm(request.form)
    user_id = form.user_id.data
    issue_id = form.issue_id.data
    units = form.units.data
    remove = form.remove.data
    # handle removal
    if remove==1:
        with db.engine.begin() as connection:
            connection.execute(f"DELETE FROM shopping_cart WHERE user_id = '{user_id}' AND issue_id = '{issue_id}'")
    # handle update
    if units==0:
        with db.engine.begin() as connection:
            connection.execute(f"DELETE FROM shopping_cart WHERE user_id = '{user_id}' AND issue_id = '{issue_id}'")
    else:
        if units > 0 and units <= max_units_available(issue_id):
            with db.engine.begin() as connection:
                connection.execute(f"UPDATE shopping_cart SET units = {units} WHERE user_id = '{user_id}' AND issue_id = '{issue_id}'")
    db.session.commit()
    session['items_in_cart'] = calculate_items_in_cart(ShoppingCart.query.filter_by(user_id=current_user.get_id()).all())
    return redirect(url_for('shopping_cart'))

@app.route('/update_shipping_method', methods=['POST'])
def update_shipping_method():
    form = UpdateShippingMethodForm(request.form)
    if form.validate_on_submit:
        session['shipping_method'] = form.shipping_method_id.data
        return redirect(url_for('shopping_cart'))
    return redirect(url_for('shopping_cart'))

@app.route('/complete_transaction', methods=['POST'])
def complete_transaction():
    # prep work
    # load default discount code
    discount_code = Discount.query.filter(Discount.code=='').first()
    # update if coupon_code is valid
    if 'coupon_code' in session:
        coupon_code = session['coupon_code']
        discount_coupon_code = Discount.query.filter(Discount.code==coupon_code).first()
        if discount_coupon_code:
            discount_code = discount_coupon_code
    shipping_method = ShippingMethod.query.filter_by(name='USPS Media Mail').first()
    # if logged in update to preferred values
    #profile = UserProfile.query.filter_by(user_id=current_user.get_id()).first()
    #if profile:
    #    shipping_method = profile.shipping_method
    #    discount = profile.discount
    # override shipping_method if it's set in the session
    #if 'shipping_method' in session:
    #    shipping_method = ShippingMethod.query.filter_by(id=session['shipping_method']).first()
    #print("Gathered info")

    # get order_id
    order_id = request.json['orderID']
    # go check paypal
    paypal = get_paypal_client(app)
    pp_request = OrdersGetRequest(order_id)
    pp_response = paypal.client.execute(pp_request)
    #print(paypal.object_to_json(pp_response))
    # if COMPLETED wrap it up!
    if pp_response.result.status=='COMPLETED':
        # collect info from paypal order
        paypal_data = {
            'pp_order_id': pp_response.result.id,
            'payer_email': pp_response.result.payer.email_address,
            'pp_create_time': pp_response.result.create_time,
            'pp_total': pp_response.result.purchase_units[0].amount.value
        }
        if hasattr(pp_response.result.purchase_units[0].shipping.name,'full_name'):
            paypal_data['pp_full_name'] = pp_response.result.purchase_units[0].shipping.name.full_name
        if hasattr(pp_response.result.purchase_units[0].shipping.address, 'address_line_1'):
            paypal_data['pp_address_line_1'] = pp_response.result.purchase_units[0].shipping.address.address_line_1
        if hasattr(pp_response.result.purchase_units[0].shipping.address, 'address_line_2'):
            paypal_data['pp_address_line_2'] = pp_response.result.purchase_units[0].shipping.address.address_line_2
        if hasattr(pp_response.result.purchase_units[0].shipping.address,'admin_area_2'):
            paypal_data['pp_admin_area_2'] = pp_response.result.purchase_units[0].shipping.address.admin_area_2
        if hasattr(pp_response.result.purchase_units[0].shipping.address,'admin_area_1'):
            paypal_data['pp_admin_area_1'] = pp_response.result.purchase_units[0].shipping.address.admin_area_1
        if hasattr(pp_response.result.purchase_units[0].shipping.address,'postal_code'):
            paypal_data['pp_postal_code'] = pp_response.result.purchase_units[0].shipping.address.postal_code
        if hasattr(pp_response.result.purchase_units[0].shipping.address,'country_code'):
            paypal_data['pp_country_code'] = pp_response.result.purchase_units[0].shipping.address.country_code

        # get cart and calculate costs
        cart = ShoppingCart.query.filter_by(user_id=current_user.get_id()).all()
        order = convert_cart_to_order(cart, paypal_data=paypal_data, discount_code=discount_code, shipping_method=shipping_method)
        # put all items into queue for removal from ebay
        send_new_order_sqs_message(order)
        if order:
            # clear cart specific session stuff
            if 'shipping_method' is session:
                session.pop('shipping_method')
            if 'coupon_code' is session:
                session.pop('coupon_code')
            # send success email
            send_invoice(order)
        else:
            print(f"Failed to convert order!")

    # todo otherwise PANIC!!!
    else:
        print(f'Status Code: {pp_response.status_code}')
        print(f'Status: {pp_response.result.status}')
        print(f'Order ID: {pp_response.result.id}')
        print(f'Intent: {pp_response.result.intent}')

    return redirect(url_for('shopping_cart'))


@app.route('/inventory', methods=['GET','POST'])
@admin_required
@login_required
def inventory():
    form = SearchInventoryForm(request.form)
    if request.method=='POST':
        # search term
        inventory_query = Inventory.query
        if form.search.data:
            search_term = form.search.data
            inventory_query = inventory_query.filter(func.upper(Inventory.title).like(f'%{search_term.upper()}%'))
        # limit publishers
        if form.publishers.data:
            publisher_id = form.publishers.data.id
            inventory_query = inventory_query.filter(Inventory.publisher_id==publisher_id)
        # filter by release date
        if form.release_date.data:
            release_date = form.release_date.data.release_date
            inventory_query = inventory_query.filter(Inventory.release_date==release_date)
        # filter by store visibility
        if form.only_show_visible.data:
            inventory_query = inventory_query.filter(Inventory.units > 0).filter(Inventory.hidden == False)
        # apply default sorting
        inventory_query = inventory_query.order_by(desc(Inventory.release_date), Inventory.title)
        inventory = inventory_query.all()
        #for item in inventory:
            #inv = InventoryItemForm()
            #inv.issue_id = item.issue_id
            #inv.title = item.title
            #inv.units = item.units
            #inv.release_date = item.release_date
            #inv.hidden = item.hidden
            #if item.ebay:
            #    inv.ebay_item_id = item.ebay.ebay_item_id
            #else:
            #    inv.ebay_item_id = ""
            #if item.sale:
            #    inv.sale = item.sale.sale_percentage
            #else:
            #    inv.sale = 0.0
            #form.inventory.append_entry(inv)
        return render_template('inventory.html', inventory=inventory, add_form=InventoryItemForm(), form=form, title="Inventory")
    inventory = Inventory.query.order_by(Inventory.title).all()
    # populate inventory subforms
    for item in inventory:
        inv = InventoryItemForm()
        inv.issue_id = item.issue_id
        inv.title = item.title
        inv.units = item.units
        inv.release_date = item.release_date
        inv.hidden = item.hidden
        if item.ebay:
            inv.ebay_item_id = item.ebay.ebay_item_id
        else:
            inv.ebay_item_id = ""
        if item.sale:
            inv.sale = item.sale.sale_percentage
        else:
            inv.sale = 0.0
        form.inventory.append_entry(inv)
    return render_template('inventory.html', inventory=inventory, add_form=InventoryItemForm(), form=form, title="Inventory")


@app.route('/add_to_inventory', methods=['POST'])
@login_required
def add_to_inventory():
    form = InventoryItemForm(request.form)
    inventory = Inventory(issue_id=form.issue_id.data, title=form.title.data, publisher_id=form.publisher.data.id, units=form.units.data, retail_price=form.retail_price.data, release_date=form.release_date.data, hidden=form.hidden.data)
    db.session.add(inventory)
    db.session.commit()
    return redirect(request.referrer)

@app.route('/edit_inventory', methods=['GET','POST'])
@admin_required
@login_required
def edit_inventory():
    form = SearchInventoryForm(request.form)
    if request.method=='POST':
        # process updates
        while len(form.inventory) > 0:
            i = form.inventory.pop_entry()
            record = Inventory.query.filter(Inventory.issue_id==i.issue_id.data).first()
            record.units = i.units.data
            record.release_date = i.release_date.data
            sale = record.sale
            if sale:
                record.sale.sale_percentage = i.sale.data
                # if the sale record exists but is set to zero, delete it
                if record.sale.sale_percentage == 0.0:
                    db.session.delete(sale)
            else:
                # if a sale record doesn't exist and the value is > 0.0, create the record
                if i.sale.data > 0.0:
                    sale = InventorySale(issue_id=i.issue_id.data, sale_percentage=i.sale.data)
                    db.session.add(sale)
            record.hidden = i.hidden.data
            db.session.add(record)
        db.session.commit()
        # search term
        inventory_query = Inventory.query
        if form.search.data:
            search_term = form.search.data
            inventory_query = inventory_query.filter(func.upper(Inventory.title).like(f'%{search_term.upper()}%'))
        # limit publishers
        if form.publishers.data:
            publisher_id = form.publishers.data.id
            inventory_query = inventory_query.filter(Inventory.publisher_id==publisher_id)
        # filter by release date
        if form.release_date.data:
            release_date = form.release_date.data.release_date
            inventory_query = inventory_query.filter(Inventory.release_date==release_date)
        # filter by store visibility
        if form.only_show_visible.data:
            inventory_query = inventory_query.filter(Inventory.units > 0).filter(Inventory.hidden == False)
        # apply default sorting
        inventory_query = inventory_query.order_by(desc(Inventory.release_date), Inventory.title)
        inventory = inventory_query.limit(200).all()
        for item in inventory:
            inv = InventoryItemForm()
            inv.issue_id = item.issue_id
            inv.title = item.title
            inv.units = item.units
            inv.release_date = item.release_date
            inv.hidden = item.hidden
            if item.ebay:
                inv.ebay_item_id = item.ebay.ebay_item_id
            else:
                inv.ebay_item_id = ""
            if item.sale:
                inv.sale = item.sale.sale_percentage
            else:
                inv.sale = 0.0
            form.inventory.append_entry(inv)
        return render_template('edit_inventory.html', inventory=inventory, add_form=InventoryItemForm(), form=form, title="Edit Inventory")
    inventory = Inventory.query.order_by(Inventory.title).limit(200).all()
    # populate inventory subforms
    for item in inventory:
        inv = InventoryItemForm()
        inv.issue_id = item.issue_id
        inv.title = item.title
        inv.units = item.units
        inv.release_date = item.release_date
        inv.hidden = item.hidden
        if item.ebay:
            inv.ebay_item_id = item.ebay.ebay_item_id
        else:
            inv.ebay_item_id = ""
        if item.sale:
            inv.sale = item.sale.sale_percentage
        else:
            inv.sale = 0.0
        form.inventory.append_entry(inv)
    return render_template('edit_inventory.html', inventory=inventory, add_form=InventoryItemForm(), form=form, title="Edit Inventory")


@app.route('/no_email', methods=['GET'])
def no_email():
    if 'email' in request.args:
        email = request.args['email']
        # try to get it, otherwise create a new one
        email_preferences = EmailPreferences.query.filter(EmailPreferences.email_address==email).first()
        if email_preferences is None:
            email_preferences = EmailPreferences(email_address=email, no_email=True)
        else:
            email_preferences.no_email = True
        db.session.add(email_preferences)
        db.session.commit()
        return f'Unsubscribe successful! {email} will no longer receive emails.'
    else:
        return ''


@app.route('/test_queue', methods=['GET'])
def test_queue():
    output = ''
    try:
        sqs = boto3.resource('sqs', region_name='us-east-1')
        queue = sqs.get_queue_by_name(QueueName='ipl-new-order-queue.fifo')
        message = 'testing'
        response = queue.send_message(MessageGroupId='OrderItem', MessageBody=message)
        return 'Message Sent'
    except Exception as inst:
        return ''.join(inst.args)
