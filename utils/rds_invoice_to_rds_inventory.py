import os
import re
import sys
import boto3
import pandas as pd
import numpy as np
import requests
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

# pandas init
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

engine = create_engine(SQLALCHEMY_DATABASE_URI)
connection = engine.connect()

invoice_date = sys.argv[1]
release_date = sys.argv[2]

order = pd.read_sql(f"select * from invoice where date = '{invoice_date}'", connection)
filtered = order[order['category_code'] == 1]
filtered = filtered[~filtered['item_description'].str.startswith("IMAGE FIRSTS")]
filtered = filtered[['item_code','item_description','units_shipped', 'retail_price', 'publisher']]
filtered['item_code'] = filtered['item_description'].apply(updateDescriptionWithUseCode).combine_first(filtered['item_code'])
filtered['title'] = filtered['item_description'].apply(titleFromDescription)
filtered['issue'] = filtered['title'].apply(issueFromTitle)
filtered = filtered.drop(['item_description'], axis=1)

for record in filtered.to_dict('records'):
    item_code = record['item_code']
    title = record['title']
    units = record['units_shipped']
    aws_image_url = f'https://ipl-subscriptions-artwork.s3.amazonaws.com/{item_code}.jpg'
    print(f"{item_code}\t{units}\t{title}")

    try:
        #insert = f"INSERT INTO inventory (issue_id, units, release_date) VALUES ('{item_code}', {units}, '{release_date}') ON CONFLICT ON CONSTRAINT inventory_issue_id_unique DO UPDATE SET units = EXCLUDED.units + {units}"
        insert = f"INSERT INTO inventory (issue_id, units, release_date) VALUES ('{item_code}', {units}, '{release_date}')"
        connection.execute(insert)
    except Exception as e:
        print(e)
        print(f"\tFailed to add {units} units of {item_code} because of an exception.")
