#import os
#import re
#import sys
#import pandas as pd
#import numpy as np
#import requests
from ebaysdk.exception import ConnectionError
from ebaysdk.trading import Connection as Trading
from sqlalchemy import create_engine
from datetime import datetime
from dateutil.parser import parse


def parse_transaction(transaction):
    return {
        'buyer_email':transaction['Buyer']['Email'],
        'buyer_zipcode':transaction['Buyer']['BuyerInfo']['ShippingAddress']['PostalCode'],
        'item_id':transaction['Item']['ItemID'],
        'listing_start_time':transaction['Item']['ListingDetails']['StartTime'],
        'listing_end_time':transaction['Item']['ListingDetails']['EndTime'],
        'title':transaction['Item']['Title'],
        'quantity':transaction['QuantityPurchased']
    }

# postgres init
SQLALCHEMY_DATABASE_URI = ""
engine = create_engine(SQLALCHEMY_DATABASE_URI)
connection = engine.connect()

transactions = []

api = Trading(config_file="ebay.yaml", domain="api.ebay.com")

try:
    data = {
        "SoldList" : {
            "Include": "true",
            "DurationInDays": 60
        }
        #"DetailLevel": "ReturnAll"
    }

    response = api.execute('GetMyeBaySelling', data)

    sold = response.dict()['SoldList']['OrderTransactionArray']['OrderTransaction']
    for s in sold:
        if 'Transaction' in s:
            # This is a simple transaction
            transaction = s['Transaction']
            t = parse_transaction(transaction)
            transactions.append(t)
        if 'Order' in s:
            # This is an order, a compound transaction
            order = s['Order']
            for transaction in order['TransactionArray']['Transaction']:
                t = parse_transaction(transaction)
                # todo combine transactions on the same item
                transactions.append(t)

except ConnectionError as e:
    print(e)
    print(e.response.dict())

print(f'Found {len(transactions)} transactions in the past 60 days.')

#for t in transactions:
#    print(t)
#    print("\n")
#exit()

for t in transactions:
    try:
        data = {
            "ItemID": t['item_id'],
            "IncludeItemSpecifics": "true"
        }
        response = api.execute('GetItem', data)
        item_specifics = response.dict()['Item']['ItemSpecifics']
        item_code = None
        if isinstance(item_specifics['NameValueList'],list):
            for i in item_specifics['NameValueList']:
                if i['Name']=='Diamond Item Code':
                    item_code = i['Value']
        insert = (
            f"INSERT INTO subscriptions.ebay_sales "
            f"(item_id, buyer_email, buyer_zipcode, item_code, listing_start_time, listing_end_time, title, quantity) VALUES "
            f"({t['item_id']},'{t['buyer_email']}','{t['buyer_zipcode']}','{item_code}','{parse(t['listing_start_time'])}','{parse(t['listing_end_time'])}','{t['title']}',{t['quantity']}) "
            #f"ON CONFLICT (item_id, buyer_email, listing_end_time) DO UPDATE SET quantity = EXCLUDED.quantity + {t['quantity']}"
            f"ON CONFLICT (item_id, buyer_email, listing_end_time) DO NOTHING"
        )
        #print(insert)
        connection.execute(insert)

    except ConnectionError as e:
        print(e)
        print(e.response.dict())
