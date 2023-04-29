from ebaysdk.exception import ConnectionError
from ebaysdk.trading import Connection as Trading
from datetime import datetime, timedelta
from dateutil.parser import parse
import random

positive_comments = [
    "Excellent buyer, thank you for your business!",
    "Thank you for an easy, pleasant transaction. Excellent buyer.",
    "A+ buyer. Indie Pull List thanks you for your business!",
    "Smooth transaction - recommended buyer! Thanks for your business!!!"
]

def parse_transaction(transaction, order_id):
    return {
        'user_id': transaction['Buyer']['UserID'],
        'item_id': transaction['Item']['ItemID'],
        'listing_end_time': parse(transaction['CreatedDate'], ignoretz=True),
        'title': transaction['Item']['Title'],
        'quantity': transaction['QuantityPurchased'],
        'transaction_id': transaction['TransactionID'],
        'order_id': order_id
    }

def lambda_handler(event, context):
    transactions = []
    api = Trading(config_file="ebay.yaml", domain="api.ebay.com")

    try:
        data = {
            "SoldList" : {
                "Include": "true",
                "OrderStatusFilter": "PaidAndShipped",
                "DurationInDays": 3
            }
        }

        response = api.execute('GetMyeBaySelling', data)
        # todo check response for no results and one results case
        #print(response.dict())

        sold = response.dict()['SoldList']['OrderTransactionArray']['OrderTransaction']
        for s in sold:
            if 'Transaction' in s:
                # This is a simple transaction
                transaction = s['Transaction']
                if 'FeedbackLeft' not in transaction:
                    t = parse_transaction(transaction, None)
                    transactions.append(t)
            if 'Order' in s:
                # This is an order, a compound transaction
                order = s['Order']
                order_id = s['Order']['OrderID']
                for transaction in order['TransactionArray']['Transaction']:
                    if 'FeedbackLeft' not in transaction:
                        t = parse_transaction(transaction, None)
                        transactions.append(t)

    except ConnectionError as e:
        print(e)
        print(e.response.dict())

    yesterday = datetime.now() - timedelta(hours=18)
    for t in transactions:
        if yesterday > t['listing_end_time']:
            print(f"{t['transaction_id']}\t{t['item_id']}\t{t['user_id']}\t{t['title']}")
            data = {
                "CommentText": random.choice(positive_comments),
                "CommentType": "Positive",
                "ItemID": t['item_id'],
                "TransactionID": t['transaction_id'],
                "TargetUser": t['user_id']
            }
            response = api.execute('LeaveFeedback', data)
            if response.dict()['Ack']!='Success':
                print(f"Error leaving feedback: {response.dict()}")
        else:
            print(f">>> READY IN {(t['listing_end_time'] - yesterday).total_seconds() // 3600} HOURS >>>\t{t['transaction_id']}\t{t['item_id']}\t{t['user_id']}\t{t['title']}")
