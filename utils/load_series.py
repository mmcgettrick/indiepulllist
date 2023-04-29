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
                f"INSERT INTO series (id, name, publisher_id, artwork_url) "
                f"select s.id, s.name, p.id as publisher_id, 'https://ipl-subscriptions-artwork.s3.amazonaws.com/' || f.first_code || '.jpg' as artwork_url "
                f"from (select CAST(\"SERIES_CODE\" as Integer) as id, INITCAP(\"MAIN_DESC\") as name, \"PUBLISHER\" as publisher "
                f"from dmd_master_data "
                f"where \"CATEGORY\" = '1' "
                f"and \"SERIES_CODE\" <> '0' "
                f"and \"PUBLISHER\" = '{publisher.upper()}' "
                f"group by \"SERIES_CODE\", \"MAIN_DESC\", \"PUBLISHER\" "
                f"order by name) as s "
                f"left join publisher p on s.publisher = upper(p.name) "
                f"left join (select DISTINCT ON (\"SERIES_CODE\") CAST(\"SERIES_CODE\" as Integer) as id, \"DIAMD_NO\" as first_code "
                f"from dmd_master_data "
                f"where \"CATEGORY\" = '1' "
                f"AND \"ISSUE_NO\" = '1' "
                f"AND \"PUBLISHER\" = '{publisher.upper()}' "
                f"order by \"SERIES_CODE\", \"STOCK_NO\") as f on s.id = f.id "
                f"order by name "
                f"ON CONFLICT (id) "
                f"DO NOTHING"
            )
            connection.execute(text(insert))

except Exception as e:
    print(e)
