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
pd.set_option('display.max_rows', 150)
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
release_date = sys.argv[1]

listable_query = (
    f"SELECT inv.issue_id as item_code, inv.units, inv.title, inv.retail_price, inv.description, pub.name as publisher, stock.stock_number "
    f"FROM inventory AS inv "
    f"LEFT JOIN inventory_ebay as ebay ON inv.issue_id = ebay.issue_id "
    f"INNER JOIN publisher as pub ON inv.publisher_id = pub.id "
    f"LEFT JOIN item_code_stock_xref as stock ON inv.issue_id = stock.item_code "
    f"WHERE inv.units > 0 "
    f"AND inv.hidden = false "
    f"AND inv.release_date = '{release_date}'"
    f"AND pub.comics = true "
    f"AND ebay.ebay_item_id IS NULL"
)
listable = pd.read_sql(listable_query, connection)
#listable['ebay_price'] = (listable['retail_price'] * 0.90).round(2)
#listable['ebay_price'] = (listable['retail_price'] * 0.95).round(2)
listable['ebay_price'] = listable['retail_price']
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
    description = f'''
    <![CDATA[<b>{title}.</b> New and unread! This is a Stock Photo.
    <p><b>Summary:</b><br>{record['description']}</p>
    <b>Shop with confidence!</b><br>
    We guarantee that this item will be in new and unread condition. All of our product goes
    directly from the distributor delivery into bags and boards and is not handled by customers at any time prior to purchase. As a result
    most all of our product is in Near Mint to Mint condition, but occasional scuffs and dents can occur in the shipment from the distibutor.
    As such, we make no guarantee of condition outside of "new and unread". If you have any questions about the condition of an item that will be
    sent to you, simply ask and we will be happy to provide photos.<br><br>
    <b>Packaging:</b><br>
    All of our products are shipped in Gemini mailers and packaged with BCW acid-free backing boards and polypropylene bags.<br><br>
    <b>!!!Please Read Our Combined Shipping Policy!!!</b><br>This is the most common question we get so please have a look!
    We offer combined shipping on orders placed by the same user on the same day. After the base shipping price of $4.25 for the first item,
    each additional item has a shipping charge of $1.25. Excess shipping charges collected by eBay will be refunded upon shipment.
    <b>We do not support eBay's "<i>request a total at checkout</i> option".</b> The buyer pays full
    shipping at checkout and a refund will be sent when the order is processed.<br><br>
    Orders ship USPS First Class for orders of 3 items or less and upgrade to USPS Priority Mail for 4 items and above
    (at no additional charge).
    <br><br>
    <b>Returns:</b><br>If the item is damaged, faulty, or doesn't match the listing description, it is covered by the eBay
    Money Back Guarantee and may be returned.<br><br>
    <b>!!!A Note On Pricing!!!</b><br>
    We sell new comic books for suggested retail price, with the exception of incentive/unlocked/chase-type covers, which generally
    follow the following pricing structure:<br>
    One-Per-Store: $19.99<br>
    1:10: $19.99<br>
    1:15: $29.99<br>
    etc... <br>
    Beyond this, you will never see an item marked up due to scarcity on the market or priced higher because it is "in demand".<br>]]>
    '''
    publisher = re.sub(r'\&', '&#038;', record['publisher'])
    #issue = record['issue']
    item = {
        'Item': {
            'Title': title,
            'Description': description,
            'ItemSpecifics': {
                'NameValueList': [
                    {'Name': 'Publisher', 'Value': publisher},
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
