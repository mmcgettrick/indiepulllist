from subscriptions import app, db
from subscriptions.email import send_tracking
from subscriptions.models import Order, OrderItem, OrderShipping
from datetime import datetime
from dateutil.parser import parse
from flask import request
from lxml.etree import CDATA, Element, SubElement, tostring

@app.route('/ship_station_endpoint', methods=['GET','POST'])
def ship_station_endpoint():
    if request.method=='GET':
        #todo add error handling
        action = request.args['action']
        start_date = parse(request.args['start_date'])
        end_date = parse(request.args['end_date'])
        #page = request.args['page']
        print(f"EndPoint GET request!")
        print(f"Start Date: {start_date}")
        print(f"End Date: {end_date}")

        #root = Element('Orders', pages='1')
        root = Element('Orders')
        orders = Order.query.filter(Order.date >= start_date).filter(Order.date <= end_date).all()
        for o in orders:
            print(f"Returning order #{o.id}")
            order = SubElement(root,'Order')
            order_id = SubElement(order,'OrderID')
            order_id.text = CDATA(f'{o.paypal_order_id}')
            order_number = SubElement(order,'OrderNumber')
            order_number.text = CDATA(f'{o.id}')
            order_date = SubElement(order,'OrderDate')
            order_date.text = CDATA(f'{o.date.strftime("%m/%d/%Y %H:%M")}') # MM/dd/yyyy HH:mm
            order_status = SubElement(order,'OrderStatus')
            order_status.text = CDATA(o.status)
            last_modified = SubElement(order,'LastModified')
            last_modified.text = CDATA(f'{o.date.strftime("%m/%d/%Y %H:%M")}') # MM/dd/yyyy HH:mm
            shipping_method = SubElement(order,'ShippingMethod')
            shipping_method.text = CDATA('USPSMediaMail') # todo maybe populate someday?
            payment_method = SubElement(order,'PaymentMethod')
            payment_method.text = CDATA('PayPal')
            order_total = SubElement(order,'OrderTotal')
            order_total.text = CDATA(f'{o.total}')
            tax_amount = SubElement(order,'TaxAmount')
            tax_amount.text = CDATA('0.00')
            shipping_amount = SubElement(order,'ShippingAmount')
            shipping_amount.text = CDATA(f'{o.shipping}')

            customer = SubElement(order,'Customer')
            customer_code = SubElement(customer,'CustomerCode')
            customer_code.text = CDATA(o.paypal_email)

            bill_to = SubElement(customer,'BillTo')
            bill_to_name = SubElement(bill_to,'Name')
            bill_to_name.text = CDATA(o.address.name)
            email = SubElement(bill_to,'Email')
            email.text = CDATA(o.paypal_email)

            ship_to = SubElement(customer,'ShipTo')
            shipping_name = SubElement(ship_to,'Name')
            shipping_name.text = CDATA(o.address.name)
            address_1 = SubElement(ship_to,'Address1')
            address_1.text = CDATA(o.address.address_1)
            if o.address.address_2:
                address_2 = SubElement(ship_to,'Address2')
                address_2.text = CDATA(o.address.address_2)
            city = SubElement(ship_to,'City')
            city.text = CDATA(o.address.admin_area_2)
            state = SubElement(ship_to,'State')
            state.text = CDATA(o.address.admin_area_1)
            postal_code = SubElement(ship_to,'PostalCode')
            postal_code.text = CDATA(o.address.postal_code)
            country = SubElement(ship_to,'Country')
            country.text = CDATA(o.address.country_code)

            items = SubElement(order,'Items')
            for i in o.items:
                item = SubElement(items,'Item')
                sku = SubElement(item,'SKU')
                sku.text = CDATA(i.issue_id)
                name = SubElement(item,'Name')
                name.text = CDATA(i.issue.title)
                image_url = SubElement(item,'ImageUrl')
                image_url.text = CDATA(f"https://d2fb3otj4xmuxd.cloudfront.net/{i.issue_id}.jpg")
                quantity = SubElement(item,'Quantity')
                quantity.text = CDATA(f'{i.units}')
                unit_price = SubElement(item,'UnitPrice')
                unit_price.text = CDATA(f'{i.discount_price}')
                weight = SubElement(item,'Weight')
                weight.text = CDATA('5')
                weight_units = SubElement(item,'WeightUnits')
                weight_units.text = CDATA('Ounces')

        return tostring(root, encoding='utf-8', xml_declaration=True)

    if request.method=='POST':
        print(f"EndPoint POST request!")
        ss_username = request.values['SS-UserName']
        ss_password = request.values['SS-Password']
        action = request.values['action']
        order_number = request.values['order_number']
        carrier = request.values['carrier']
        service = request.values['service']
        tracking_number = request.values['tracking_number']

        print(ss_username)

        # Save tracking_number for order_number
        order = Order.query.filter(Order.id==order_number).first()
        order.tracking_number = tracking_number
        order.status = 'shipped'
        db.session.add(order)
        db.session.commit()

        send_tracking(order)

        return ('', 200)
