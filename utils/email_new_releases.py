import boto3
import re
from botocore.exceptions import ClientError, DataNotFoundError
from sqlalchemy import create_engine
from time import sleep

class Issue():
    def __init__(self, id, title, publisher):
        self.id = id
        self.title = title
        self.publisher = publisher

    def get_series(self):
        return re.search("[^#]*",self.title).group(0)

    def get_store_link(self):
        return f'http://indiepulllist.com/comics/{self.id}'

    def get_image_link(self):
        return f'https://d2fb3otj4xmuxd.cloudfront.net/{self.id}.jpg'


def get_style():
    return '''
        .button {
            background-color: #4CAF50;
            border: none;
            color: white !important;
            display: inline-block;
            font-weight: bold;
            margin-top: 4px;
            padding: 8px;
            text-align: center;
            text-decoration: none;
            width: 80px;
        }
        .card {
            box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2);
            display: inline-block;
            margin: 8px;
            transition: 0.3s;
            vertical-align: top;
            width: 340px;
        }
        .container {
            padding: 4px 16px;
        }
        .image {
            width:120px;
            float:left;
            padding: 4px;
            padding-right: 8px;
        }
    '''


def create_issue_card(issue):
    card = (
        f'<div class="card">'
        f'  <img class="image" src="{issue.get_image_link()}"/>'
        f'  <div class="container">'
        f'    <b>{issue.title}</b><br>{issue.publisher}<br>'
        f'    <a class="button" href="{issue.get_store_link()}">Buy Now!</a>'
        f'  </div>'
        f'</div>'
    )
    return card


def send_email(email, client, body_text, body_html):
    subject = "Indie Pull List: New releases for this week!"
    charset = "UTF-8"

    try:
        response = client.send_email(
            Source='IndiePullList.com <store@indiepulllist.com>',
            Destination={
                'ToAddresses': [
                    email
                ]
            },
            Message={
                'Body': {
                    'Html': {
                        'Charset': charset,
                        'Data': body_html
                    },
                    'Text': {
                        'Charset': charset,
                        'Data': body_text
                    }
                },
                'Subject': {
                    'Charset': charset,
                    'Data': subject
                },
            },
            ReturnPath='store@indiepulllist.com'
        )
        #print(f"Response: {response}")
    except ClientError as e:
        print(f"Client Error: {e.response['Error']['Message']}")
        print(e.response)
    except DataNotFoundError as e:
        print(f"Data Not Found Error: {e.response['Error']['Message']}")
    else:
        print("Email sent! Message ID:"),
        print(response['MessageId'])

client = boto3.client(
    'ses',
    aws_access_key_id='AKIA2ZW4G6XSK4OXGUGC',
    aws_secret_access_key='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',
    region_name='us-east-1')

# postgres init
HOST='RDS_HOST_GOES_HERE'
PORT='5432'
DATABASE='RDS_DB_GOES_HERE'
USER='RDS_USER_GOES_HERE'
PASSWORD='RDS_PW_GOES_HERE'
SQLALCHEMY_DATABASE_URI = f"postgresql://{USER}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}"
engine = create_engine(SQLALCHEMY_DATABASE_URI)
connection = engine.connect()

query = (
    f"select issue_id, title, p.name as publisher from inventory i "
    f"join publisher p on i.publisher_id = p.id "
    f"where p.comics = true and hidden = false and units > 0 and release_date >= CURRENT_DATE "
    f"order by title"
)
rs = connection.execute(query)
results = rs.fetchall()
text = 'Indie Pull List\nNew releases for this week!\nhttp://indiepulllist.com/store\n\n'
html = ''
html += '<!DOCTYPE html>'
html += f'<html><head><meta name="viewport" content="width=device-width, initial-scale=1"><style>{get_style()}</style></head><body>'
html += '<h2 style="margin-left: 16px;">INDIE PULL LIST<h2>'
html += '<h3 style="margin-left: 16px;">New releases for this week!</h3>'
#html += '<h3 style="margin-left: 16px;">Note: Diamond (the primary comic distributor in the US) is having significant shipping delays. We are unlikely to have this week\'s product in hand until Friday.</h3>'
for r in results:
    issue = Issue(r[0], r[1], r[2])
    html += create_issue_card(issue)
    text += f'{issue.title}\n'

endhtml = "<p>To unsubscribe from this and all other unsolicited Indie Pull List emails <a href='http://indiepulllist.com/no_email?email={email}'>click here</a>.</p></body></html>"

# TEST email
#send_email('mark.mcgettrick@gmail.com',client, text, html + endhtml.format(email='mark.mcgettrick@gmail.com'))
#exit()

send_email('gosaben@gmail.com',client, text, html + endhtml.format(email='gosaben@gmail.com'))

i=0
ebay_query = "select distinct(buyer_email) from ebay_sales where buyer_email not like '%%members.ebay.com' and buyer_email not in (select email_address from email_preferences where no_email = true) order by buyer_email"
print(ebay_query)
ebay_buyers = (buyer[0] for buyer in connection.execute(ebay_query))
for buyer in ebay_buyers:
    print(f"{buyer} sending...")
    send_email(buyer, client, text, html + endhtml.format(email=buyer))
    sleep(0.1)
    i = i+1
print(f'Sent {i} emails to ebay buyers\n\n')#

i=0
buyers = (buyer[0] for buyer in connection.execute("select distinct(LOWER(paypal_email)) as email from \"order\" where LOWER(paypal_email) not in (select email_address from email_preferences where no_email = true) order by email"))
for buyer in buyers:
    print(f"{buyer} sending...")
    send_email(buyer, client, text, html + endhtml.format(email=buyer))
    sleep(0.1)
    i = i+1
print(f'Sent {i} emails to website buyers')
