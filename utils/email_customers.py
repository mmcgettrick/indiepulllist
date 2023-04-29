import boto3
from botocore.exceptions import ClientError, DataNotFoundError
from sqlalchemy import create_engine
from time import sleep

def send_email(email, client):
    subject = "Back Issue Sale: SAVE 50% ON BACK ISSUES AT INDIE PULL LIST!"
    body_text = """
Indie Pull List

SAVE 50% ON BACK ISSUES!

Save big and round out your collection!

*All issues (excluding incentive covers) released prior to January 2022 are now 50% off!

Visit us at IndiePullList.com!
    """
    body_html = """
<!doctype html>
<html lang="en">

<head>
  <!-- Required meta tags -->
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
  <style>

  </style>
  <title>IndiePullList</title>
</head>
<body style="font-family: sans-serif; text-align: center">
  <div style="background-color: black; color: white; padding: 20px;">
    <h1>Indie Pull List</h1>
    <h2><span style="color: red">BACK ISSUE SALE!</span></h2>
    <h3>SAVE 50% ON ALL BACK ISSUES!</h3>
    <h3>Save big and round out your collection!</h3>
    <p>
      All issues (excluding incentive covers) released prior to January 2022 are now 50% off!<br>
      Visit us at <a href="http://www.indiepulllist.com/comics?on_sale=y" style="color: white">IndiePullList.com</a>!
    </p>
    <img src="https://ipl-subscriptions-artwork.s3.amazonaws.com/SplashMedium.jpg" style="max-width: 100%"></img>
  </div>
</body>
</html>
    """
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
    aws_access_key_id='',
    aws_secret_access_key= '',
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

# TEST email
send_email('mark.mcgettrick@gmail.com',client, text, html + endhtml.format(email='mark.mcgettrick@gmail.com'))
exit()

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
