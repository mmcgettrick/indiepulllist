import boto3
import sys
from subscriptions import app, db
from subscriptions.models import Inventory, InventoryEbay, Order, OrderItem, OrderShipping
from flask_login import current_user, LoginManager, login_manager


def calculate_unit_discount(item, discount_code):
    return round(item.inventory.sale_or_retail_price() * discount_code.percentage, 2)

def calculate_discount(shopping_cart, discount_code):
    discount = 0
    for item in shopping_cart:
        unit_discount = calculate_unit_discount(item, discount_code)
        discount += (unit_discount * item.units)
    return discount

def calculate_subtotal(shopping_cart):
    subtotal = 0
    for item in shopping_cart:
        subtotal = subtotal + (item.inventory.sale_or_retail_price() * item.units)
    return subtotal


def calculate_shipping(shopping_cart, shipping_method, discount_code):
    # return quick if free shipping
    if discount_code.free_shipping==True:
        return 0
    total_units = 0
    for item in shopping_cart:
        total_units += item.units
    return shipping_method.base_price #+ ((total_units - 1) * shipping_method.incremental_price)

def calculate_items_in_cart(shopping_cart):
    count = 0
    for item in shopping_cart:
        count += item.units
    return count

# convert the shopping cart to an order
def convert_cart_to_order(cart, paypal_data=None, discount_code=None, shipping_method=None):
    # make the calculations for the jump to lightspeed
    subtotal = calculate_subtotal(cart)
    discount = calculate_discount(cart, discount_code)
    shipping = calculate_shipping(cart, shipping_method, discount_code)
    total = subtotal - discount + shipping

    # sanity check that totals match!
    if paypal_data['pp_total']==str(total):
        # convert cart or order and clear cart
        order = Order(user_id=current_user.get_id(), paypal_order_id=paypal_data['pp_order_id'], paypal_email=paypal_data['payer_email'], subtotal=subtotal, discount=discount, shipping=shipping, total=total, coupon_code=discount_code.code, date=paypal_data['pp_create_time'], status='paid')
        db.session.add(order)
        db.session.commit()
        order_shipping = OrderShipping(order_id=order.id,name=paypal_data['pp_full_name'],address_1=paypal_data['pp_address_line_1'],admin_area_2=paypal_data['pp_admin_area_2'],admin_area_1=paypal_data['pp_admin_area_1'],postal_code=paypal_data['pp_postal_code'],country_code=paypal_data['pp_country_code'])
        if 'pp_address_line_2' in paypal_data:
            order_shipping.address_2 = paypal_data['pp_address_line_2']
        db.session.add(order_shipping)
        db.session.commit()
        for item in cart:
            discount_price = item.inventory.sale_or_retail_price() - calculate_unit_discount(item, discount_code)
            total_price = item.inventory.sale_or_retail_price() * item.units
            db.session.add(OrderItem(order_id=order.id, issue_id=item.issue_id, units=item.units, unit_price=item.inventory.sale_or_retail_price(), discount_price=discount_price, total_price=total_price))
            inventory = Inventory.query.filter(Inventory.issue_id==item.issue_id).first()
            new_units = inventory.units - item.units
            # todo sanity check this number
            inventory.units = new_units
            db.session.delete(item)
            db.session.commit()
        return order
    else:
        return None


# group inventory
def group_inventory(inventory, sort_directive):
    grouped_inventory = {}
    if sort_directive=='newest':
        for i in inventory:
            if i.release_date in grouped_inventory:
                grouped_inventory[i.release_date].append(i)
            else:
                grouped_inventory[i.release_date] = [i]
        return grouped_inventory
    # Title > Newest
    elif sort_directive=='title_az':
        for i in inventory:
            if i.title[0] in grouped_inventory:
                grouped_inventory[i.title[0]].append(i)
            else:
                grouped_inventory[i.title[0]] = [i]
        return grouped_inventory
    # Publisher > Newest > Title
    elif sort_directive=='publisher_newest':
        for i in inventory:
            if i.publisher.name in grouped_inventory:
                if i.release_date in grouped_inventory[i.publisher.name]:
                    grouped_inventory[i.publisher.name][i.release_date].append(i)
                else:
                    grouped_inventory[i.publisher.name][i.release_date] = [i]
            else:
                grouped_inventory[i.publisher.name] = {}
                if i.release_date in grouped_inventory[i.publisher.name]:
                    grouped_inventory[i.publisher.name][i.release_date].append(i)
                else:
                    grouped_inventory[i.publisher.name][i.release_date] = [i]
        return grouped_inventory
    # Publisher > Title > Newest
    elif sort_directive=='publisher_az':
        for i in inventory:
            if i.publisher.name in grouped_inventory:
                if i.title[0] in grouped_inventory[i.publisher.name]:
                    grouped_inventory[i.publisher.name][i.title[0]].append(i)
                else:
                    grouped_inventory[i.publisher.name][i.title[0]] = [i]
            else:
                grouped_inventory[i.publisher.name] = {}
                if i.title[0] in grouped_inventory[i.publisher.name]:
                    grouped_inventory[i.publisher.name][i.title[0]].append(i)
                else:
                    grouped_inventory[i.publisher.name][i.title[0]] = [i]
        return grouped_inventory
    else:
        for i in inventory:
            if i.release_date in grouped_inventory:
                grouped_inventory[i.release_date].append(i)
            else:
                grouped_inventory[i.release_date] = [i]
        return grouped_inventory


# return the maximum units currently available for purchase
def max_units_available(issue_id):
    return 10

def send_new_order_sqs_message(order):
    try:
        sqs = boto3.resource('sqs', region_name='us-east-1')
        queue = sqs.get_queue_by_name(QueueName='ipl-new-order-queue.fifo')
        for item in order.items:
            # first look up the ebay item id
            inventory_ebay = InventoryEbay.query.filter(InventoryEbay.issue_id==item.issue_id).first()
            # don't send a message unless there is an ebay listing
            if inventory_ebay is not None:
                message = f'{{"order_id":{order.id},"issue_id":"{item.issue_id}","units":{item.units},"ebay_item_id":"{inventory_ebay.ebay_item_id}"}}'
                response = queue.send_message(MessageGroupId='OrderItem', MessageBody=message)
    except Exception as e:
        error_message = ''.join(e.args)
        print(error_message, file=sys.stderr)
        raise
