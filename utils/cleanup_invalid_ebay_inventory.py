from ebaysdk.exception import ConnectionError
from ebaysdk.trading import Connection as Trading
from sqlalchemy import create_engine

api = Trading(config_file="ebay.yaml", domain="api.ebay.com")

HOST='RDS_HOST_GOES_HERE'
PORT='5432'
DATABASE='RDS_DB_GOES_HERE'
USER='RDS_USER_GOES_HERE'
PASSWORD='RDS_PW_GOES_HERE'
SQLALCHEMY_DATABASE_URI = f"postgresql://{USER}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}"
engine = create_engine(SQLALCHEMY_DATABASE_URI)
connection = engine.connect()

rs = connection.execute('select * from inventory_ebay order by ebay_item_id')
results = rs.fetchall()
for result in results:
    issue_id = result[0]
    ebay_item_id = result[1]
    print(f'{issue_id} {ebay_item_id}')
    try:
        data = {
            "ItemID" : ebay_item_id
        }
        response = api.execute('GetItem', data)
    except ConnectionError as e:
        # remove record from inventory_ebay
        connection.execute(f"delete from inventory_ebay where issue_id = '{issue_id}'")
        print(f'{issue_id} cleared of ebay id: {ebay_item_id}')
