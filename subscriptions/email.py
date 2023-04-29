from subscriptions import app
import boto3
from botocore.exceptions import ClientError, DataNotFoundError
from flask import render_template, url_for
from itsdangerous import URLSafeTimedSerializer


def confirm_token(token, expiration=3600):
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    try:
        email = serializer.loads(
            token,
            salt=app.config['SECURITY_PASSWORD_SALT'],
            max_age=expiration
        )
    except:
        return False
    return email


def generate_confirmation_token(email):
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    return serializer.dumps(email, salt=app.config['SECURITY_PASSWORD_SALT'])


def send_tracking(order):
    subject = f"IndiePullList Order #{order.paypal_order_id}"

    # TODO
    body_text = f"Your order has been prepared for shipment. Your tracking number is {order.tracking_number}."
    body_html = f"<html><body>Your order has been prepared for shipment. Your tracking number is <a href='https://tools.usps.com/go/TrackConfirmAction?tRef=fullpage&tLc=2&text28777=&tLabels={order.tracking_number}%2C&tABt=false'>{order.tracking_number}</a>.</body></html>"

    charset = "UTF-8"
    client = boto3.client('ses', region_name='us-east-1')

    try:
        response = client.send_email(
            Source='store@indiepulllist.com',
            Destination={
                'ToAddresses': [
                    order.paypal_email
                ],
                'BccAddresses': [
                    'store@indiepulllist.com'
                ]
            },
            Message={
                'Body': {
                    'Html': {
                        'Charset': charset,
                        'Data': body_html
                    },
                    'Text': {
                        'Charset': charset,
                        'Data': body_text
                    }
                },
                'Subject': {
                    'Charset': charset,
                    'Data': subject
                },
            },
            ReturnPath='store@indiepulllist.com'
        )
        print(f"Response: {response}")
    except ClientError as e:
        print(f"Client Error: {e.response['Error']['Message']}")
        print(e.response)
    except DataNotFoundError as e:
        print(f"Data Not Found Error: {e.response['Error']['Message']}")
    else:
        print("Email sent! Message ID:"),
        print(response['MessageId'])


def send_invoice(order):
    subject = f"IndiePullList Order #{order.paypal_order_id}"
    body_text = render_template('order_email.txt', order=order)
    body_html = render_template('order_email.html', order=order)
    charset = "UTF-8"

    client = boto3.client('ses', region_name='us-east-1')

    try:
        #response = client.list_verified_email_addresses()
        #print(response)

        response = client.send_email(
            Source='store@indiepulllist.com',
            Destination={
                'ToAddresses': [
                    order.paypal_email
                ],
                'BccAddresses': [
                    'store@indiepulllist.com'
                ]
            },
            Message={
                'Body': {
                    'Html': {
                        'Charset': charset,
                        'Data': body_html
                    },
                    'Text': {
                        'Charset': charset,
                        'Data': body_text
                    }
                },
                'Subject': {
                    'Charset': charset,
                    'Data': subject
                },
            },
            ReturnPath='store@indiepulllist.com'
        )
        print(f"Response: {response}")
    except ClientError as e:
        print(f"Client Error: {e.response['Error']['Message']}")
        print(e.response)
    except DataNotFoundError as e:
        print(f"Data Not Found Error: {e.response['Error']['Message']}")
    else:
        print("Email sent! Message ID:"),
        print(response['MessageId'])


def send_confirmation(email):
    token = generate_confirmation_token(email)
    confirm_url = url_for('confirm_email', token=token, _external=True)
    subject = "IndiePullList Email Confirmation"
    body_text = render_template('confirmation_email.txt', email=email, confirm_url=confirm_url)
    body_html = render_template('confirmation_email.html', email=email, confirm_url=confirm_url)
    charset = "UTF-8"

    client = boto3.client('ses', region_name='us-east-1')

    try:
        response = client.send_email(
            Source='store@indiepulllist.com',
            Destination={
                'ToAddresses': [
                    email
                ],
                'BccAddresses': [
                    'store@indiepulllist.com'
                ]
            },
            Message={
                'Body': {
                    'Html': {
                        'Charset': charset,
                        'Data': body_html
                    },
                    'Text': {
                        'Charset': charset,
                        'Data': body_text
                    }
                },
                'Subject': {
                    'Charset': charset,
                    'Data': subject
                },
            },
            ReturnPath='store@indiepulllist.com'
        )
        print(f"Response: {response}")
    except ClientError as e:
        print(f"Client Error: {e.response['Error']['Message']}")
        print(e.response)
    except DataNotFoundError as e:
        print(f"Data Not Found Error: {e.response['Error']['Message']}")
    else:
        print("Email sent! Message ID:"),
        print(response['MessageId'])


def send_fcbd2021_confirmation(order, issues):
    subject = "IndiePullList FCBD2021 Confirmation"

    order_text = ''
    order_html = ''
    for i in issues:
        order_text += f'{i[0]} {i[1]}\n'
        order_html += f'{i[0]} {i[1]}<br>'
    if 'bagboard' in order:
        order_text += f'Your order will be bagged and boarded at a cost of $0.50 per title.\n'
        order_html += f'Your order will be bagged and boarded at a cost of $0.50 per title.<br>'

    body_text = f"Your FCBD2021 order request has been received. We will send a PayPal invoice when your order has been processed and is ready to ship.\n\n{order_text}"
    body_html = f"<html><body>Your FCBD2021 order request has been received. We will send a PayPal invoice when your order has been processed and is ready to ship.<br><br>{order_html}</body></html>"

    charset = "UTF-8"
    client = boto3.client('ses', region_name='us-east-1')

    try:
        response = client.send_email(
            Source='store@indiepulllist.com',
            Destination={
                'ToAddresses': [
                    order['paypal_email']
                ],
                'BccAddresses': [
                    'store@indiepulllist.com'
                ]
            },
            Message={
                'Body': {
                    'Html': {
                        'Charset': charset,
                        'Data': body_html
                    },
                    'Text': {
                        'Charset': charset,
                        'Data': body_text
                    }
                },
                'Subject': {
                    'Charset': charset,
                    'Data': subject
                },
            },
            ReturnPath='store@indiepulllist.com'
        )
        print(f"Response: {response}")
    except ClientError as e:
        print(f"Client Error: {e.response['Error']['Message']}")
        print(e.response)
    except DataNotFoundError as e:
        print(f"Data Not Found Error: {e.response['Error']['Message']}")
    else:
        print("Email sent! Message ID:"),
        print(response['MessageId'])
