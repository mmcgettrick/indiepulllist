import boto3
import json
import pandas as pd
import re

from datetime import *
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta
from io import StringIO
from sqlalchemy import create_engine

# Parse simple invoice
def parse_simple_invoice(data, filename):
    columns = ['units_shipped', 'item_code', 'item_description', 'retail_price', 'unit_price', 'invoice_amount', 'category_code', 'order_type', 'publisher']
    invoice = pd.read_csv(data, names=columns, header=None, skiprows=4)
    invoice['date'] = filename.replace('.csv','')
    invoice['date'] = pd.to_datetime(invoice['date'])
    invoice['discount_code'] = invoice.item_code.str.strip().str[-1]
    invoice['item_code'] = invoice.item_code.str.strip().str[:-1]
    return invoice

# Parse standard invoice
def parse_standard_invoice(data, filename):
    columns = ['units_shipped', 'item_code', 'discount_code', 'item_description', 'retail_price', 'unit_price', 'invoice_amount', 'category_code', 'order_type', 'processed_as', 'order_number', 'upc_code', 'isbn_code', 'ean_code', 'po_number', 'allocated_code', 'publisher', 'series_code']
    dtypes = {'ean_code': object, 'isbn_code': object, 'upc_code': object}
    invoice = pd.read_csv(data, names=columns, header=None, dtype=dtypes, skiprows=4)
    invoice['date'] = filename.replace('.csv','')
    invoice['date'] = pd.to_datetime(invoice['date'])
    invoice['discount_code'] = invoice.discount_code.str.strip()
    return invoice

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

def calculate_release_date(invoice_name):
    invoice_name = invoice_name.replace('.csv','')
    invoice_date = parse(invoice_name)
    release_date = invoice_date + relativedelta(days=+8)
    return release_date

HOST='RDS_HOST_GOES_HERE'
PORT='5432'
DATABASE='RDS_DB_GOES_HERE'
USER='RDS_USER_GOES_HERE'
PASSWORD='RDS_PW_GOES_HERE'
SQLALCHEMY_DATABASE_URI = f"postgresql://{USER}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}"

s3 = boto3.resource('s3')
origin_bucket = 'ipl-invoices'

def lambda_handler(event, context):

    for key in event.get('Records'):
        object_key = key['s3']['object']['key']
        print(f"Processing {object_key}")

        invoice_obj = s3.Object(
            bucket_name=origin_bucket,
            key=object_key,
        )
        obj_body = invoice_obj.get()['Body'].read()
        data = obj_body.decode('utf-8')

        check = pd.read_csv(StringIO(data), header=None, skiprows=4)
        columns = len(check.columns)
        invoice = None
        if columns==18:
            invoice = parse_standard_invoice(StringIO(data), object_key)
        else:
            invoice = parse_simple_invoice(StringIO(data), object_key)

        engine = create_engine(SQLALCHEMY_DATABASE_URI)
        connection = engine.connect()
        invoice.to_sql('invoice', engine, if_exists='append', index=False)

        print(f'Inserted {len(invoice.index)} records from {object_key}.')

        # figure out release date for these issues
        invoice_date = parse(object_key.replace('.csv',''))
        release_date = calculate_release_date(object_key)
        print(f"Calculated release date is {release_date}")

        order = pd.read_sql((
            f"with pl as (select name, id from publisher) "
            f"select b.item_code, coalesce(i.title,b.item_description) as item_description, b.units_shipped, b.retail_price, i.description, coalesce(s.publisher_id, pl.id) as publisher_id from ( "
            f"	select item_code, item_description, sum(units_shipped) as units_shipped, publisher, retail_price from ( "
            f"		select item_code, item_description, units_shipped, retail_price, publisher "
            f"    	from invoice "
            f"		where date = '{invoice_date}' and category_code = 1 AND units_shipped > 0 "
            f"	) as foo "
            f"	group by item_code, item_description, publisher, retail_price "
            f") as b "
            f"left join issues as i on b.item_code = i.item_code "
            f"left join series as s on i.series_id = s.id "
            f"left join pl on b.publisher = upper(pl.name) "
            f"order by item_code"), connection)


        filtered = order[~order['item_description'].str.startswith("IMAGE FIRSTS")]
        filtered['item_code'] = filtered['item_description'].apply(updateDescriptionWithUseCode).combine_first(filtered['item_code'])
        filtered['title'] = filtered['item_description'].apply(titleFromDescription)
        filtered['issue'] = filtered['title'].apply(issueFromTitle)
        filtered = filtered.drop(['item_description'], axis=1)
        #print(filtered)

        for record in filtered.to_dict('records'):
            item_code = record['item_code']
            title = record['title'].replace("'","''")
            units = record['units_shipped']
            description = record['description'].replace("'","''") if record['description'] else ''
            retail_price = record['retail_price']
            publisher_id = record['publisher_id']
            try:
                print(f"Adding {item_code}\t{units}\t{title}")
                insert = f"INSERT INTO inventory (issue_id, units, release_date, hidden, title, description, retail_price, publisher_id) VALUES ('{item_code}', {units}, '{release_date}', true, '{title}', '{description}', {retail_price}, {publisher_id}) ON CONFLICT DO NOTHING"
                connection.execute(insert)
            except Exception as e:
                print(f"\tFailed to add {units} units of {item_code} because of an exception.")
                print(e)
