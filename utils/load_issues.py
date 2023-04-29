import pandas as pd
from sqlalchemy import create_engine, text
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
            insert = (
                f"INSERT INTO issues (title, item_code, series_id, foc_date, est_ship_date, retail_price, category_code, issue_number, variant) "
                f"SELECT REGEXP_REPLACE(REGEXP_REPLACE(title,'\(MR*\)*$',''),'\(Net\)\s*$','') as title, "
                f"item_code, series_id, foc_date, est_ship_date, retail_price, category_code, issue_number, variant "
                f"FROM (SELECT \"FULL_TITLE\" as title, \"DIAMD_NO\" as item_code, CAST(\"SERIES_CODE\" as Integer) as series_id, "
                f"CAST(\"FOC_DATE\" as date) as foc_date, CAST(\"SHIP_DATE\" as date) as est_ship_date, "
                f"CAST(\"SRP\" as numeric) as retail_price, CAST(\"CATEGORY\" as Integer) as category_code, "
                f"CASE WHEN \"ISSUE_NO\" is null THEN 0 "
                f"ELSE CAST(\"ISSUE_NO\" as Integer) "
                f"END as issue_number, "
                f"CASE WHEN \"VARIANT_DESC\" SIMILAR TO '%CVR [B-Z]%' THEN true "
                f"ELSE false "
                f"END as variant "
                f"FROM dmd_master_data "
                f"WHERE \"PUBLISHER\" = '{publisher.upper()}' "
                f"AND \"CATEGORY\" = '1' "
                f"AND CAST(\"FOC_DATE\" as date) > '2019-06-01' "
                f"ORDER BY \"FULL_TITLE\""
                f") AS raw_issues "
                f"WHERE title not like '% INCV %' "
                f"ON CONFLICT (item_code) "
                f"DO NOTHING"
            )
            connection.execute(text(insert))

except Exception as e:
    print(e)
