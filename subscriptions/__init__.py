from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__, instance_relative_config=True)
app.config.from_object('config')
app.config.from_pyfile('config.py')

if 'MODE' in os.environ:
    app.config['MODE'] = os.environ['MODE']

if 'RDS_HOSTNAME' in os.environ:
    HOST = os.environ['RDS_HOSTNAME']
    PORT = os.environ['RDS_PORT']
    DATABASE = os.environ['RDS_DB_NAME']
    USER = os.environ['RDS_USERNAME']
    PASSWORD = os.environ['RDS_PASSWORD']
    SQLALCHEMY_DATABASE_URI = f"postgresql://{USER}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}"
    app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI

db = SQLAlchemy(app)

if 'PAYPAL_CLIENT_ID' in os.environ:
    app.config['PAYPAL_CLIENT_ID'] = os.environ['PAYPAL_CLIENT_ID']
    app.config['PAYPAL_SECRET'] = os.environ['PAYPAL_SECRET']

from subscriptions import routes
from subscriptions import blog
from subscriptions import series
from subscriptions import ship_station
from subscriptions import store
from subscriptions import subscriptions
