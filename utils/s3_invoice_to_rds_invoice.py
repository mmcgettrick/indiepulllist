import os
import re
import sys
import boto3
import pandas as pd
import numpy as np
import requests
from botocore.exceptions import ClientError
from io import StringIO
from sqlalchemy import create_engine

# Parse simple invoice
def parse_simple_invoice(data):
    columns = ['units_shipped', 'item_code', 'item_description', 'retail_price', 'unit_price', 'invoice_amount', 'category_code', 'order_type', 'publisher']
    invoice = pd.read_csv(data, names=columns, header=None, skiprows=4)
    invoice['date'] = filename.replace('../data/','').replace('.csv','')
    invoice['date'] = pd.to_datetime(invoice['date'])
    invoice['discount_code'] = invoice.item_code.str.strip().str[-1]
    invoice['item_code'] = invoice.item_code.str.strip().str[:-1]
    return invoice

# Parse standard invoice
def parse_standard_invoice(data):
    columns = ['units_shipped', 'item_code', 'discount_code', 'item_description', 'retail_price', 'unit_price', 'invoice_amount', 'category_code', 'order_type', 'processed_as', 'order_number', 'upc_code', 'isbn_code', 'ean_code', 'po_number', 'allocated_code', 'publisher', 'series_code']
    dtypes = {'ean_code': object, 'isbn_code': object, 'upc_code': object}
    invoice = pd.read_csv(data, names=columns, header=None, dtype=dtypes, skiprows=4)
    invoice['date'] = filename.replace('../data/','').replace('.csv','')
    invoice['date'] = pd.to_datetime(invoice['date'])
    invoice['discount_code'] = invoice.discount_code.str.strip()
    return invoice

# pandas config
pd.set_option('display.max_columns', 50)
pd.set_option('display.max_colwidth', 100)
pd.set_option('display.width', 220)
pd.set_option('mode.chained_assignment', None)

# DB init
HOST='RDS_HOST_GOES_HERE'
PORT='5432'
DATABASE='RDS_DB_GOES_HERE'
USER='RDS_USER_GOES_HERE'
PASSWORD='RDS_PW_GOES_HERE'
SQLALCHEMY_DATABASE_URI = f"postgresql://{USER}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}"

# AWS client init
s3 = boto3.client(
    's3',
    aws_access_key_id='',
    aws_secret_access_key='',
    region_name='us-east-1')

try:
    filename = f'{sys.argv[1]}.csv'
    print(f"Getting: {filename}")
    response = s3.get_object(Bucket='ipl-invoices',Key=filename)
    data = response['Body'].read().decode('utf-8')
    #print(data)
    check = pd.read_csv(StringIO(data), header=None, skiprows=4)
    columns = len(check.columns)
    invoice = None
    if columns==18:
        invoice = parse_standard_invoice(StringIO(data))
    else:
        invoice = parse_simple_invoice(StringIO(data))

    #print(invoice)
    engine = create_engine(SQLALCHEMY_DATABASE_URI)
    invoice.to_sql('invoice', engine, if_exists='append', index=False)

except ClientError as e:
    print(e)
