#import os
#import re
#import sys
import pandas as pd
#import numpy as np
#import requests
#from sqlalchemy import create_engine

from ebaysdk.exception import ConnectionError
from ebaysdk.trading import Connection as Trading
from datetime import datetime, timedelta


def parse_item(item):
    return {
        'item_id':item['ItemID'],
        'title':item['Title'],
        'quantity':item['Quantity'],
        'quantity_available':item['QuantityAvailable'],
        'time_left':item['TimeLeft']
    }

active_items = []

api = Trading(config_file="ebay.yaml", domain="api.ebay.com")

try:
    data = {
        "ActiveList" : {
            "Include": "true"
        }
    }

    response = api.execute('GetMyeBaySelling', data)
    pages = int(response.dict()['ActiveList']['PaginationResult']['TotalNumberOfPages'])
    for i in range(0, pages):
        data = {
            "ActiveList" : {
                "Include": "true",
                "Pagination": {
                    "PageNumber": i+1
                }
            }
        }
        response = api.execute('GetMyeBaySelling', data)
        active = response.dict()['ActiveList']['ItemArray']['Item']
        for item in active:
            active_items.append(parse_item(item))

except ConnectionError as e:
    print(e)
    print(e.response.dict())

print(f'Found {len(active_items)} active items.')

c = 1
for item in active_items:
    try:
        data = {
            "ItemID": item['item_id'],
            "IncludeItemSpecifics": "true"
        }
        response = api.execute('GetItem', data)
        start_time = response.dict()['Item']['ListingDetails']['StartTime']
        category_id = response.dict()['Item']['PrimaryCategory']['CategoryID']
        #category_name = response.dict()['Item']['PrimaryCategory']['CategoryName']
        item_code = None
        if 'ItemSpecifics' in response.dict()['Item']:
            item_specifics = response.dict()['Item']['ItemSpecifics']
            if isinstance(item_specifics['NameValueList'],list):
                for s in item_specifics['NameValueList']:
                    if s['Name']=='Diamond Item Code':
                        item_code = s['Value']
        item['start_time'] = start_time
        item['category_id'] = int(category_id)
        #item['category_name'] = category_name
        item['item_code'] = item_code
        print(c)
        c = c+1

    except ConnectionError as e:
        print(e)
        print(e.response.dict())

pd.set_option('display.max_columns', 50)
pd.set_option('display.max_colwidth', 100)
pd.set_option('display.max_rows', 500)
pd.set_option('display.width', 220)
pd.set_option('mode.chained_assignment', None)

item_df = pd.DataFrame.from_dict(active_items)
item_df.set_index('item_id', inplace=True)
item_df['start_time'] = pd.to_datetime(item_df['start_time'])
item_df.sort_values(['start_time'], inplace=True)
just_comics = item_df[item_df['category_id']==77]
# find items over 90 days old that have not sold any items
comics_older_than_ninety_days = just_comics[just_comics['start_time'] < (pd.to_datetime('10/13/2019', utc=True) - pd.Timedelta(days=60))]
#unsold_comics_older_than_ninety_days = comics_older_than_ninety_days[comics_older_than_ninety_days['quantity']==comics_older_than_ninety_days['quantity_available']]

print(comics_older_than_ninety_days)
