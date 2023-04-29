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
pd.set_option('display.max_rows', 100)
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

engine = create_engine(SQLALCHEMY_DATABASE_URI)
connection = engine.connect()
listable_query = (
    f"SELECT inv.issue_id as item_code, inv.units, inv.title, inv.retail_price, inv.description, pub.name as publisher, stock.stock_number "
    f"FROM inventory AS inv "
    f"LEFT JOIN inventory_ebay as ebay ON inv.issue_id = ebay.issue_id "
    f"INNER JOIN publisher as pub ON inv.publisher_id = pub.id "
    f"LEFT JOIN item_code_stock_xref as stock ON inv.issue_id = stock.item_code "
    f"WHERE inv.units > 0 "
    f"AND inv.hidden = false "
    f"AND ebay.ebay_item_id IS NULL"
)
listable = pd.read_sql(listable_query, connection)
#listable['ebay_price'] = (listable['retail_price'] * 0.90).round(2)
listable['ebay_price'] = (listable['retail_price'] * 0.95).round(2)
listable = listable.sort_values(by=['title'])
print(listable)
#exit()

api = Trading(config_file="ebay.yaml", domain="api.ebay.com")
for record in listable.to_dict('records'):
    print(f'> {record["item_code"]} {record["title"]}')
    s3_filename = f'{record["item_code"]}.jpg'
    aws_image = f'https://ipl-subscriptions-artwork.s3.amazonaws.com/{s3_filename}'
    print(aws_image)

    # get latest image!!!
    if record["stock_number"]:
        diamond_url = f'https://retailerservices.diamondcomics.com/Image/ItemMainImageLowRes/{record["stock_number"]}.jpg'
        print(f'Downloading {record["stock_number"]}.jpg from Diamond')
        tmpfile = f'tmp/{record["stock_number"]}.jpg'
        with open(tmpfile, "wb") as file:
            response = requests.get(diamond_url)
            file.write(response.content)
        # upload tmpfile to S3
        print(f"Uploading {s3_filename} to S3")
        response = s3.upload_file(tmpfile, 'ipl-subscriptions-artwork', s3_filename)
        # remove tmp file
        os.remove(tmpfile)

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
    description = f"<![CDATA[<b>{title}. New and unread! Stock Photo.</b><br><br>All Indie Pull List comics are packaged with BCW acid-free backing boards and polypropylene bags. All orders are shipped in Gemini Comic Mailers to ensure that your comics arrive minty fresh!<br><br><b>Combined Shipping:</b><br>We offer combined shipping on orders placed by the same user on the same day. After the base shipping price for the first issue, each additional issue is $1.25. Excess shipping charges will be refunded upon shipment. Orders of more than 4 items automatically upgrade to USPS Priority Mail for no additional charge.<br><br><b>Returns:</b><br>If the item is damaged, faulty, or doesn't match the listing description, it is covered by the eBay Money Back Guarantee and may be returned. <p><b>Summary:</b><br>{record['description']}</p>]]>"
    publisher = re.sub(r'\&', '&#038;', record['publisher'])
    #issue = record['issue']
    item = {
        'Item': {
            'Title': title,
            'Description': description,
            'ItemSpecifics': {
                'NameValueList': [
                    {'Name': 'Publisher', 'Value': publisher},
                    #{'Name': 'Issue Number', 'Value': issue},
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
            #'PaymentMethods': 'PayPal',
            #'PayPalEmailAddress': 'indiepulllist@gmail.com',
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
                'ReturnsWithinOption': 'Days_30',
                'ReturnsWithin': '30 Days',
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
                    'ShippingService': 'USPSFirstClass',
                    'ShippingServiceCost': '4.25',
                    'ShippingServiceAdditionalCost': '1.25'
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
        #response = api.execute('VerifyAddFixedPriceItem', item)
        #print(response.dict())
        response = api.execute('AddFixedPriceItem', item)
        if response.dict()['Ack'] == 'Success':
            print(f"\tListed {record['item_code']} on eBay")
            item_id = response.dict()['ItemID']
            print(f"Inserting {item_id} as ebay_item_id")
            connection.execute(f"INSERT INTO inventory_ebay (issue_id, ebay_item_id) VALUES ('{record['item_code']}', {item_id}) ON CONFLICT DO NOTHING")
            print(f"\tSet {record['item_code']} ebay_item_id to {item_id}")
        elif response.dict()['Ack'] == 'Warning':
            print(response.dict())
            print(f"\tListed {record['item_code']} on eBay")
            item_id = response.dict()['ItemID']
            print(f"Inserting {item_id} as ebay_item_id")
            connection.execute(f"INSERT INTO inventory_ebay (issue_id, ebay_item_id) VALUES ('{record['item_code']}', {item_id}) ON CONFLICT DO NOTHING")
            print(f"\tSet {record['item_code']} ebay_item_id to {item_id}")
        else:
            print(response.dict())

    except Exception as e:
        print(e)
        print("Failed to add to eBay- probably duplicate:")
        print(f"\t{item_code} {title} {quantity} ${price} {aws_image}")
