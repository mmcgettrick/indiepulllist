# requires:
#   layer: pandas
#   layer: postgres

import boto3
import pandas as pd

from io import StringIO
from sqlalchemy import create_engine, text

HOST='RDS_HOST_GOES_HERE'
PORT='5432'
DATABASE='RDS_DB_GOES_HERE'
USER='RDS_USER_GOES_HERE'
PASSWORD='RDS_PW_GOES_HERE'
SQLALCHEMY_DATABASE_URI = f"postgresql://{USER}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}"

s3 = boto3.resource('s3')
origin_bucket = 'ipl-diamond-data'

def lambda_handler(event, context):

    for key in event.get('Records'):
        object_key = key['s3']['object']['key']
        print(f"Processing {object_key}")

        invoice_obj = s3.Object(
            bucket_name=origin_bucket,
            key=object_key,
        )
        obj_body = invoice_obj.get()['Body'].read()
        data = obj_body.decode('latin_1')

        engine = create_engine(SQLALCHEMY_DATABASE_URI)
        master = pd.read_csv(StringIO(data), delimiter='\t', dtype=object)
        #print(master.head())

        master.to_sql('dmd_master_data', engine, if_exists='append', index=False, schema='public')

        with engine.begin() as connection:
            # load creators
            load_writers = (
                f"INSERT INTO creator (name) "
                f"SELECT DISTINCT(a.name) FROM ( "
	                f"SELECT (substring(\"WRITER\" from ',(.*?)$') || ' ' || substring(\"WRITER\" from '^(.*?),')) as name "
	                f"FROM dmd_master_data "
	                f"WHERE \"CATEGORY\" = '1' "
	                f"AND \"SERIES_CODE\" != '0' "
                f") as a "
                f"WHERE a.name is not null "
                f"ORDER BY a.name "
                f"ON CONFLICT (name) "
                f"DO NOTHING"
            )
            connection.execute(text(load_writers))

            load_artists = (
                f"INSERT INTO creator (name) "
                f"SELECT DISTINCT(a.name) FROM ( "
	                f"SELECT (substring(\"ARTIST\" from ',(.*?)$') || ' ' || substring(\"ARTIST\" from '^(.*?),')) as name "
	                f"FROM dmd_master_data "
	                f"WHERE \"CATEGORY\" = '1' "
	                f"AND \"SERIES_CODE\" != '0' "
                f") as a "
                f"WHERE a.name is not null "
                f"ORDER BY a.name "
                f"ON CONFLICT (name) "
                f"DO NOTHING"
            )
            connection.execute(text(load_artists))

            load_colorists = (
                f"INSERT INTO creator (name) "
                f"SELECT DISTINCT(a.name) FROM ( "
	                f"SELECT (substring(\"COLORIST\" from ',(.*?)$') || ' ' || substring(\"COLORIST\" from '^(.*?),')) as name "
	                f"FROM dmd_master_data "
	                f"WHERE \"CATEGORY\" = '1' "
	                f"AND \"SERIES_CODE\" != '0' "
                f") as a "
                f"WHERE a.name is not null "
                f"ORDER BY a.name "
                f"ON CONFLICT (name) "
                f"DO NOTHING"
            )
            connection.execute(text(load_colorists))

            publishers = [publisher[0] for publisher in connection.execute(f"SELECT name FROM publisher")]
            for publisher in publishers:
                connection.execute(f"INSERT INTO item_code_stock_xref SELECT \"DIAMD_NO\", \"STOCK_NO\" FROM dmd_master_data WHERE (\"CATEGORY\" = '1' OR \"CATEGORY\" = '3' OR \"CATEGORY\" = '4') AND \"PUBLISHER\" = '{publisher.upper()}' ON CONFLICT (item_code, stock_number) DO NOTHING")

                load_series = (
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
                connection.execute(text(load_series))

                # populate creators
                populate_writers = (
                    f"INSERT INTO creator_series (creator_id, creator_role_id, series_id) "
                    f"SELECT d.id as creator_id, c.id as role_id, a.series_id FROM ( "
	                    f"SELECT DISTINCT ON (writer, series_id) (substring(\"WRITER\" from ',(.*?)$') || ' ' || substring(\"WRITER\" from '^(.*?),')) as writer, CAST(\"SERIES_CODE\" as Integer) as series_id, 'Writer' as role "
	                    f"FROM dmd_master_data "
	                    f"WHERE \"CATEGORY\" = '1' "
	                    f"AND \"SERIES_CODE\" != '0' "
                    f") as a "
                    f"INNER JOIN series AS b ON a.series_id = b.id "
                    f"INNER JOIN creator_role AS c ON a.role = c.name "
                    f"INNER JOIN creator AS d ON d.name = a.writer "
                    f"ON CONFLICT (creator_id, creator_role_id, series_id) "
                    f"DO NOTHING"
                )
                connection.execute(text(populate_writers))

                populate_artists = (
                    f"INSERT INTO creator_series (creator_id, creator_role_id, series_id) "
                    f"SELECT d.id as creator_id, c.id as role_id, a.series_id FROM ( "
	                    f"SELECT DISTINCT ON (artist, series_id) (substring(\"ARTIST\" from ',(.*?)$') || ' ' || substring(\"ARTIST\" from '^(.*?),')) as artist, CAST(\"SERIES_CODE\" as Integer) as series_id, 'Artist' as role "
	                    f"FROM dmd_master_data "
	                    f"WHERE \"CATEGORY\" = '1' "
	                    f"AND \"SERIES_CODE\" != '0' "
                    f") as a "
                    f"INNER JOIN series AS b ON a.series_id = b.id "
                    f"INNER JOIN creator_role AS c ON a.role = c.name "
                    f"INNER JOIN creator AS d ON d.name = a.artist "
                    f"ON CONFLICT (creator_id, creator_role_id, series_id) "
                    f"DO NOTHING"
                )
                connection.execute(text(populate_artists))

                populate_colorists = (
                    f"INSERT INTO creator_series (creator_id, creator_role_id, series_id) "
                    f"SELECT d.id as creator_id, c.id as role_id, a.series_id FROM ( "
	                    f"SELECT DISTINCT ON (colorist, series_id) (substring(\"COLORIST\" from ',(.*?)$') || ' ' || substring(\"COLORIST\" from '^(.*?),')) as colorist, CAST(\"SERIES_CODE\" as Integer) as series_id, 'Colorist' as role "
	                    f"FROM dmd_master_data "
	                    f"WHERE \"CATEGORY\" = '1' "
	                    f"AND \"SERIES_CODE\" != '0' "
                    f") as a "
                    f"INNER JOIN series AS b ON a.series_id = b.id "
                    f"INNER JOIN creator_role AS c ON a.role = c.name "
                    f"INNER JOIN creator AS d ON d.name =a.colorist "
                    f"ON CONFLICT (creator_id, creator_role_id, series_id) "
                    f"DO NOTHING"
                )
                connection.execute(text(populate_colorists))

                load_issues = (
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
                    f"AND \"SHIP_DATE\" IS NOT NULL "
                    f"ORDER BY \"FULL_TITLE\""
                    f") AS raw_issues "
                    f"WHERE title not like '% INCV %' "
                    f"ON CONFLICT (item_code) "
                    f"DO NOTHING"
                )
                connection.execute(text(load_issues))
