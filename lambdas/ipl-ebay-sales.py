# requires:
#   ebay.yaml
#   layer: ebaysdk
#   layer: postgres
from ebaysdk.exception import ConnectionError
from ebaysdk.trading import Connection as Trading
from sqlalchemy import create_engine
from datetime import datetime, timedelta
from dateutil.parser import parse

def parse_transaction(transaction, order_id):
    return {
        'buyer_email': transaction['Buyer']['Email'],
        'buyer_zipcode': transaction['Buyer']['BuyerInfo']['ShippingAddress']['PostalCode'],
        'item_id': transaction['Item']['ItemID'],
        'listing_start_time': transaction['Item']['ListingDetails']['StartTime'],
        'listing_end_time': transaction['CreatedDate'],
        'title': transaction['Item']['Title'],
        'quantity': transaction['QuantityPurchased'],
        'subtotal': transaction['TotalTransactionPrice']['value'],
        'transaction_id': transaction['TransactionID'],
        'order_id': order_id
    }

HOST='RDS_HOST_GOES_HERE'
PORT='5432'
DATABASE='RDS_DB_GOES_HERE'
USER='RDS_USER_GOES_HERE'
PASSWORD='RDS_PW_GOES_HERE'
SQLALCHEMY_DATABASE_URI = f"postgresql://{USER}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}"

def lambda_handler(event, context):
    engine = create_engine(SQLALCHEMY_DATABASE_URI)
    connection = engine.connect()

    result = connection.execute("select max(listing_end_time) from ebay_sales")
    max = result.fetchone()[0]
    print(f'Last sale before run is {max}')

    transactions = []
    api = Trading(config_file="ebay.yaml", domain="api.ebay.com")

    try:
        data = {
            "SoldList" : {
                "Include": "true",
                "DurationInDays": 1
            }
        }

        response = api.execute('GetMyeBaySelling', data)

        if 'SoldList' not in response.dict():
            print('No new results.')
            return

        entries = int(response.dict()['SoldList']['PaginationResult']['TotalNumberOfEntries'])
        print(f"{entries} entries in the result.")
        if entries == 0:
            return

        sold = response.dict()['SoldList']['OrderTransactionArray']['OrderTransaction']
        if entries == 1:
            print("Only one result - special ")
            print(sold)
        else:
            for s in sold:
                if 'Transaction' in s:
                    # This is a simple transaction
                    transaction = s['Transaction']
                    t = parse_transaction(transaction, None)
                    transactions.append(t)
                if 'Order' in s:
                    # This is an order, a compound transaction
                    order = s['Order']
                    order_id = s['Order']['OrderID']
                    for transaction in order['TransactionArray']['Transaction']:
                        t = parse_transaction(transaction, order_id)
                        transactions.append(t)

    except ConnectionError as e:
        print(e)
        print(e.response.dict())

    print(f'Found {len(transactions)} transactions in the past day.')

    for t in transactions:
        try:
            data = {
                "ItemID": t['item_id'],
                "IncludeItemSpecifics": "true"
            }
            response = api.execute('GetItem', data)
            item_specifics = response.dict()['Item']['ItemSpecifics']
            item_code = None
            if isinstance(item_specifics['NameValueList'],list):
                for i in item_specifics['NameValueList']:
                    if i['Name']=='Diamond Item Code':
                        item_code = i['Value']
            item_code = f"'{item_code}'" if item_code else 'null'
            escaped_title = t['title'].replace('\'','\'\'')
            order_id = f"'{t['order_id']}'" if t['order_id'] else 'null'
            insert = (
                f"INSERT INTO ebay_sales "
                f"(item_id, buyer_email, buyer_zipcode, item_code, listing_start_time, listing_end_time, title, quantity, subtotal, transaction_id, order_id) VALUES "
                f"({t['item_id']},'{t['buyer_email']}','{t['buyer_zipcode']}',{item_code},'{parse(t['listing_start_time'])}','{parse(t['listing_end_time'])}','{escaped_title}',{t['quantity']},{t['subtotal']},'{t['transaction_id']}', {order_id}) "
                f"ON CONFLICT (item_id, buyer_email, listing_end_time) DO NOTHING"
            )
            connection.execute(insert)

        except ConnectionError as e:
            print(e)
            print(e.response.dict())

    # attempt to sync with inventory
    result = connection.execute(f"select item_code, quantity from ebay_sales where listing_end_time > '{max}'")
    for r in result:
        item_code = r[0]
        units = r[1]
        print(f"Remove {units} units of {item_code} from inventory.")
        store_units = connection.execute(f"select units from inventory where issue_id = '{item_code}'").fetchone()[0]
        if store_units > 0:
            connection.execute(f"update inventory set units = {store_units - units} where issue_id = '{item_code}'")
