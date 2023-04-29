import pandas as pd
from sqlalchemy import create_engine
import string
import sys

HOST='RDS_HOST_GOES_HERE'
PORT='5432'
DATABASE='RDS_DB_GOES_HERE'
USER='RDS_USER_GOES_HERE'
PASSWORD='RDS_PW_GOES_HERE'
SQLALCHEMY_DATABASE_URI = f"postgresql://{USER}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}"

try:
    engine = create_engine(SQLALCHEMY_DATABASE_URI)
    for publisher in sys.argv[1:]:
        publisher = publisher.strip('\"')
        print(f"Loading {publisher}")
        with engine.begin() as connection:
            connection.execute(f"INSERT INTO publisher (name) VALUES ('{publisher}') ON CONFLICT (name) DO NOTHING")
            connection.execute(f"INSERT INTO item_code_stock_xref SELECT \"DIAMD_NO\", \"STOCK_NO\" FROM dmd_master_data WHERE (\"CATEGORY\" = '1' OR \"CATEGORY\" = '3' OR \"CATEGORY\" = '4') AND \"PUBLISHER\" = '{publisher.upper()}' ON CONFLICT (item_code, stock_number) DO NOTHING")
except Exception as e:
    print(e)
