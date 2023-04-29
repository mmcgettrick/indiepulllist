import os
import re
import sys
import boto3
import pandas as pd
import numpy as np
import requests
from ebaysdk.trading import Connection as Trading
from sqlalchemy import create_engine

# If it starts with something like (USE JUL198621) return the code, otherwise None
def updateDescriptionWithUseCode(description):
    m = re.match(r"\(USE\s([A-Z]{3}\d{6})\)", description)
    if m:
        return m.group(1)
    else:
        return None

def titleFromDescription(description):
    return re.sub(r'^\(.*?\)', '', re.sub(r'\s\(MR\)$', '', description))

# Extract the issue e.g. #1 from the title
def issueFromTitle(title):
    m = re.search(r'#(\d+)', title)
    if m:
        return m.group(1)
    else:
        return None

# AWS client init
s3 = boto3.client(
    's3',
    aws_access_key_id='',
    aws_secret_access_key='',
    region_name='us-east-1')

pd.set_option('display.max_columns', 50)
pd.set_option('display.max_colwidth', 100)
pd.set_option('display.width', 220)
pd.set_option('mode.chained_assignment', None)

# postgres init
HOST='RDS_HOST_GOES_HERE'
PORT='5432'
DATABASE='RDS_DB_GOES_HERE'
USER='RDS_USER_GOES_HERE'
PASSWORD='RDS_PW_GOES_HERE'
SQLALCHEMY_DATABASE_URI = f"postgresql://{USER}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}"

release_date = sys.argv[1]

engine = create_engine(SQLALCHEMY_DATABASE_URI)
connection = engine.connect()
listable_query = (
    f"SELECT iss.item_code, inv.units, iss.title, iss.retail_price, iss.issue_number as issue, iss.description, pub.name as publisher, stock.stock_number "
    f"FROM inventory AS inv "
    f"INNER JOIN issues as iss ON iss.item_code = inv.issue_id "
    f"INNER JOIN series as ser ON iss.series_id = ser.id "
    f"INNER JOIN publisher as pub ON ser.publisher_id = pub.id "
    f"INNER JOIN item_code_stock_xref as stock ON iss.item_code = stock.item_code "
    f"WHERE release_date = '{release_date}' AND inv.units > 0"
)
listable = pd.read_sql(listable_query, connection)
listable['ebay_price'] = (listable['retail_price'] * 0.90).round(2)
listable = listable.sort_values(by=['title'])
print(listable)
exit()

api = Trading(config_file="ebay.yaml", domain="api.ebay.com")
for record in listable.to_dict('records'):
    print(f'> {record["item_code"]}')
    # check if img already on S3 - if not there: acquire!
    s3_filename = f'{record["item_code"]}.jpg'
    aws_image = f'https://ipl-subscriptions-artwork.s3.amazonaws.com/{s3_filename}'

    # upload image to ebay (referencing the AWS image)
    pictureData = {
        "WarningLevel": "High",
        "ExternalPictureURL": aws_image,
        "PictureName": s3_filename
    }
    response = api.execute('UploadSiteHostedPictures', pictureData)
    ebay_image_url = response.dict()['SiteHostedPictureDetails']['FullURL']

    # insert listng to eBay
    item_code = record['item_code']
    title = re.sub(r'\&', '&#038;', record['title'])
    quantity = record['units']
    price = record['ebay_price']
    description = f"<![CDATA[<b>{title}. New and unread! Stock Photo.</b><br><br>All Indie Pull List comics are packaged with BCW acid-free backing boards and polypropylene bags. All orders are shipped in Gemini Comic Mailers to ensure that your comics arrive minty fresh!<br><br><b>Combined Shipping:</b><br>We always attempt to combine shipping on orders placed by the same user on the same day (*although, orders placed more than an hour apart might get shipped separately as we are processing orders throughout the day). After the base shipping price for the first issue, each additional issue is $1.00. Excess shipping charges charged by eBay will be refunded via PayPal.<br><br><b>Returns:</b><br>If the item is damaged, faulty, or doesn't match the listing description, it is covered by the eBay Money Back Guarantee and may be returned. <p><b>Summary:</b><br>{record['description']}</p>]]>"
    publisher = record['publisher']
    issue = record['issue']
    item = {
        'Item': {
            'Title': title,
            'Description': description,
            'ItemSpecifics': {
                'NameValueList': [
                    {'Name': 'Publisher', 'Value': publisher},
                    {'Name': 'Issue Number', 'Value': issue},
                    {'Name': 'Diamond Item Code', 'Value': item_code}
                ]
            },
            'ListingDuration': 'GTC',
            'ListingType': 'FixedPriceItem',
            'Location': 'Framingham, Massachusetts',
            'PostalCode': '01701',
            'Country': 'US',
            'Currency': 'USD',
            'AutoPay': 'true',
            'PaymentMethods': 'PayPal',
            'PayPalEmailAddress': 'indiepulllist@gmail.com',
            'PrimaryCategory': {
                'CategoryID': '77',
                'CategoryName': 'Collectibles:Comics:Modern Age (1992-Now):Other Modern Age Comics'
            },
            'PictureDetails': {'PictureURL': ebay_image_url},
            'PrivateListing': 'false',
            'StartPrice': price,
            'Quantity': quantity,
            'Storefront': {
                'StoreCategoryID': '32808254018',
                'StoreCategory2ID': '0',
                'StoreURL': 'https://stores.ebay.com/indiepulllist'
            },
            'ReturnPolicy': {
                'RefundOption': 'MoneyBack',
                'Refund': 'Money Back',
                'ReturnsWithinOption': 'Days_14',
                'ReturnsWithin': '14 Days',
                'ReturnsAcceptedOption': 'ReturnsAccepted',
                'ReturnsAccepted': 'Returns Accepted',
                'ShippingCostPaidByOption': 'Buyer',
                'ShippingCostPaidBy': 'Buyer',
                'InternationalReturnsAcceptedOption': 'ReturnsNotAccepted'
            },
            'ConditionDescription': 'New',
            'DispatchTimeMax': '2',
            'ShippingDetails': {
                'ShippingType': 'Flat',
                'ShippingServiceOptions': [
                {
                    'ShippingServicePriority': '1',
                    'ShippingService': 'USPSMedia',
                    'ShippingServiceCost': '3.50',
                    'ShippingServiceAdditionalCost': '1.00'
                },
                {
                    'ShippingServicePriority': '2',
                    'ShippingService': 'USPSPriority',
                    'ShippingServiceCost': '7.95',
                    'ShippingServiceAdditionalCost': '1.00'
                }]
            },
            'ShippingPackageDetails': {
                'WeightMajor': '0',
                'WeightMinor': '8'
            },
            'ShipToLocations': 'US',
            'Site': 'US'
        }
    }
    try:
        response = api.execute('VerifyAddFixedPriceItem', item)
        #print(response.dict())
        #response = api.execute('AddFixedPriceItem', item)
        if response.dict()['Ack'] != 'Success':
            print(response.dict())
        else:
            print(f"\tListed {record['item_code']} on eBay")
    except:
        print("Failed to add to eBay- probably duplicate:")
        print(f"\t{item_code} {title} {quantity} ${price} {aws_image}")
