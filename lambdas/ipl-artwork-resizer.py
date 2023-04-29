# requires:
#   layer: PIL

import boto3
import PIL
from PIL import Image
from io import BytesIO
#from os import path

s3 = boto3.resource('s3')
origin_bucket = 'ipl-subscriptions-artwork'
destination_bucket_180 = 'ipl-artwork-180px'
width_size_180 = 180

def lambda_handler(event, context):

    for key in event.get('Records'):
        object_key = key['s3']['object']['key']
        print(f"Processing {object_key}")

        # Grabs the source file
        obj = s3.Object(
            bucket_name=origin_bucket,
            key=object_key,
        )
        obj_body = obj.get()['Body'].read()

        # Resizing the image
        img = Image.open(BytesIO(obj_body))
        wpercent = (width_size_180 / float(img.size[0]))
        hsize = int((float(img.size[1]) * float(wpercent)))
        img = img.resize((width_size_180, hsize), PIL.Image.ANTIALIAS)
        buffer = BytesIO()
        img.save(buffer, 'JPEG')
        buffer.seek(0)

        # Uploading the image
        obj = s3.Object(
            bucket_name=destination_bucket_180,
            key=object_key,
        )
        obj.put(Body=buffer)

        # Printing to CloudWatch
        print('File saved at {}/{}'.format(
            destination_bucket_180,
            object_key,
        ))
