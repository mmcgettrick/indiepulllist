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

# postgres init
HOST='RDS_HOST_GOES_HERE'
PORT='5432'
DATABASE='RDS_DB_GOES_HERE'
USER='RDS_USER_GOES_HERE'
PASSWORD='RDS_PW_GOES_HERE'
SQLALCHEMY_DATABASE_URI = f"postgresql://{USER}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}"
engine = create_engine(SQLALCHEMY_DATABASE_URI)
connection = engine.connect()
dmd_master_data = pd.read_sql("select * from subscriptions.dmd_master_data", connection)
dmd_master_data.set_index('DIAMD_NO', inplace=True)
stock = dmd_master_data['STOCK_NO']

order = pd.read_sql("select * from subscriptions.invoice where date = '2019-10-08'", connection)
filtered = order[order['category_code'] == 1]
filtered = filtered[~filtered['item_description'].str.startswith("IMAGE FIRSTS")]
filtered = filtered[['item_code','item_description','units_shipped', 'retail_price', 'publisher']]
filtered['ebay_price'] = (filtered['retail_price'] * 0.90).round(2)
filtered['item_code'] = filtered['item_description'].apply(updateDescriptionWithUseCode).combine_first(filtered['item_code'])
filtered['title'] = filtered['item_description'].apply(titleFromDescription)
filtered['issue'] = filtered['title'].apply(issueFromTitle)
filtered = filtered.drop(['item_description'], axis=1)
filtered = filtered.set_index('item_code')

joined = filtered.merge(stock, how='left', left_index=True, right_index=True)


pd.set_option('display.max_columns', 50)
pd.set_option('display.max_colwidth', 100)
pd.set_option('display.width', 220)
pd.set_option('mode.chained_assignment', None)
#print(joined)

# if item lacks an STL then log it for manual load
errors = joined[joined['STOCK_NO'].isnull()]
print("### ERRORS ###")
print(errors)
print()

listable = joined[joined['STOCK_NO'].notnull()]
listable['diamond_img_url'] = listable['STOCK_NO'].apply(lambda x: f'https://retailerservices.diamondcomics.com/Image/ItemMainImageLowRes/{x}.jpg')
listable = listable.reset_index()
#listable['item_code'] = listable['index']

#print(listable)

#exit()

api = Trading(config_file="ebay.yaml", domain="api.ebay.com")
for record in listable.to_dict('records'):
    print(f'> {record["item_code"]}')
    # check if img already on S3 - if not there: acquire!
    s3_filename = f'{record["item_code"]}.jpg'
    aws_image = f'https://ipl-subscriptions-artwork.s3.amazonaws.com/{s3_filename}'
    try:
        content = s3.head_object(Bucket='ipl-subscriptions-artwork',Key=s3_filename)
        print(f"\tFound {s3_filename} on S3")
    except:
        # download tmpfile img from Diamond
        print(f"\tDownloading {record['item_code']}.jpg from Diamond")
        tmpfile = f"tmp/{record['item_code']}.jpg"
        with open(tmpfile, "wb") as file:
            response = requests.get(record['diamond_img_url'])
            file.write(response.content)
        # upload tmpfile to S3
        print(f"\tUploading {s3_filename} to S3")
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
    quantity = record['units_shipped']
    price = record['ebay_price']
    description = f"<![CDATA[<b>{title}. VF/NM condition. Stock Photo.</b><br><br>All Indie Pull List comics are packaged with BCW acid-free backing boards and polypropylene bags. All orders are shipped in Gemini Comic Mailers to ensure that your comics arrive minty fresh!<br><br><b>Combined Shipping:</b><br>We always attempt to combine shipping on orders placed by the same user on the same day (*although, orders placed more than an hour apart might get shipped separately as we are processing orders throughout the day). After the base shipping price for the first issue, each additional issue is $1.00. Excess shipping charges charged by eBay will be refunded via PayPal.<br><br><b>Returns:</b><br>If the item is damaged, faulty, or doesn't match the listing description, it is covered by the eBay Money Back Guarantee and may be returned. ]]>"
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
        #response = api.execute('AddFixedPriceItem', item)
        if response.dict()['Ack'] != 'Success':
            print(response.dict())
        else:
            print(f"\tListed {record['item_code']} on eBay")
            # If successfully listed on eBay, add the inventory to my store
            try:
                insert = f"INSERT INTO subscriptions.inventory (issue_id, units) VALUES ('{item_code}', {quantity}) ON CONFLICT ON CONSTRAINT inventory_issue_id_unique DO UPDATE SET units = EXCLUDED.units + {quantity}"
                connection.execute(insert)
                #print("Skipping insert into inventory...")
            # handle if the issue doesn't exist (breaks foreign key constraint)
            except:
                print(f"\tFailed to add {quantity} units of {item_code} because of an exception.")
                print(f"\t{item_code} {title} {quantity} ${price} {aws_image}")
    except:
        print("Failed to add to eBay- probably duplicate:")
        print(f"\t{item_code} {title} {quantity} ${price} {aws_image}")


#1 Figure out correct way to collapse duplicate index entries
#2 Adjust for owner purchases
#3 Add dimensions to package
#4 Add check for listing fee
