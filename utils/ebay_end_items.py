#import os
#import re
import sys
#import numpy as np
#import requests
#from sqlalchemy import create_engine

from ebaysdk.exception import ConnectionError
from ebaysdk.trading import Connection as Trading

items = sys.argv
items.pop(0)

api = Trading(config_file="ebay.yaml", domain="api.ebay.com")

try:
    for item in items:
        data = {
            "EndingReason" : "NotAvailable",
            "ItemID" : item
        }
        response = api.execute('EndItem', data)
        if response.dict()['Ack']=='Success':
            print(f'Ended listing #{item}.')
        else:
            print(response.dict())

except ConnectionError as e:
    print(e)
    print(e.response.dict())
