import pandas as pd
from sqlalchemy import create_engine
import sys

filename = sys.argv[1]
columns = ['units_shipped', 'item_code', 'discount_code', 'item_description', 'retail_price', 'unit_price', 'invoice_amount', 'category_code', 'order_type', 'processed_as', 'order_number', 'upc_code', 'isbn_code', 'ean_code', 'po_number', 'allocated_code', 'publisher', 'series_code']
dtypes = {'ean_code': object, 'upc_code': object}
invoice = pd.read_csv(filename, names=columns, header=None, dtype=dtypes, skiprows=4)
invoice['date'] = filename.replace('../data/','').replace('.csv','')
invoice['date'] = pd.to_datetime(invoice['date'])
invoice['discount_code'] = invoice.discount_code.str.strip()

HOST='RDS_HOST_GOES_HERE'
PORT='5432'
DATABASE='RDS_DB_GOES_HERE'
USER='RDS_USER_GOES_HERE'
PASSWORD='RDS_PW_GOES_HERE'
SQLALCHEMY_DATABASE_URI = f"postgresql://{USER}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}"

engine = create_engine(SQLALCHEMY_DATABASE_URI)

invoice.to_sql('invoice', engine, if_exists='append', index=False)
