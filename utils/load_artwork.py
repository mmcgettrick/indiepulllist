import boto3
import pandas as pd
import os
import requests
from sqlalchemy import create_engine
import sys

# AWS client init
s3 = boto3.client(
    's3',
    aws_access_key_id='',
    aws_secret_access_key='',
    region_name='us-east-1')

HOST='RDS_HOST_GOES_HERE'
PORT='5432'
DATABASE='RDS_DB_GOES_HERE'
USER='RDS_USER_GOES_HERE'
PASSWORD='RDS_PW_GOES_HERE'
SQLALCHEMY_DATABASE_URI = f"postgresql://{USER}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}"
engine = create_engine(SQLALCHEMY_DATABASE_URI)

connection = engine.connect()
results = connection.execute("select item_code, stock_number from item_code_stock_xref order by stock_number desc")
for item_code, stock_number in results:
    diamond_url = f'https://retailerservices.diamondcomics.com/Image/ItemMainImageLowRes/{stock_number}.jpg'
    s3_filename = f'{item_code}.jpg'
    try:
        # If we have the artwork already this will not throw and exception
        content = s3.head_object(Bucket='ipl-subscriptions-artwork',Key=s3_filename)
        print(f"Found {s3_filename} on S3")
    except:
        # download tmpfile img from Diamond
        print(f"Downloading {stock_number}.jpg from Diamond")
        tmpfile = f"tmp/{stock_number}.jpg"
        with open(tmpfile, "wb") as file:
            response = requests.get(diamond_url)
            file.write(response.content)
        # upload tmpfile to S3
        print(f"Uploading {s3_filename} to S3")
        response = s3.upload_file(tmpfile, 'ipl-subscriptions-artwork', s3_filename)
        # remove tmp file
        os.remove(tmpfile)

connection.close()
