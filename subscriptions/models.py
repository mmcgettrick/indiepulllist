from subscriptions import db
from datetime import datetime, timezone
from flask_login import UserMixin
from sqlalchemy.orm import relationship
import pytz
import re


class BlogEntry(db.Model):
    __tablename__ = 'blog'
    id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.String(255), nullable=False)
    date = db.Column(db.Date, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    text = db.Column(db.String(), nullable=False)
    store_link = db.Column(db.String(255))


class Creator(db.Model):
    __tablename__ = 'creator'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)


class CreatorRole(db.Model):
    __tablename__ = 'creator_role'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)


class CreatorSeries(db.Model):
    __tablename__ = 'creator_series'
    id = db.Column(db.Integer, primary_key=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('creator.id'), nullable=False)
    creator = relationship("Creator")
    creator_role_id = db.Column(db.Integer, db.ForeignKey('creator_role.id'), nullable=False)
    creator_role = relationship("CreatorRole")
    series_id = db.Column(db.Integer, db.ForeignKey('series.id'), nullable=False)
    series = relationship("Series")


class Discount(db.Model):
    __tablename__ = 'discount'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    percentage = db.Column(db.Numeric, nullable=False)
    code = db.Column(db.String(20), nullable=False)
    free_shipping = db.Column(db.Boolean, nullable=False)
    disabled = db.Column(db.Boolean, nullable=False)
    referral_email = db.Column(db.String(120))
    owner_email = db.Column(db.String(120))


class EmailPreferences(db.Model):
    __tablename__ = 'email_preferences'
    email_address = db.Column(db.String(255), primary_key=True)
    no_email = db.Column(db.Boolean, nullable=False)


class Inventory(db.Model):
    __tablename__ = 'inventory'
    issue_id = db.Column(db.Integer, db.ForeignKey('issues.item_code'), primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(), nullable=True)
    units = db.Column(db.Integer, nullable=False)
    retail_price = db.Column(db.Numeric, nullable=False)
    release_date = db.Column(db.Date, nullable=False)
    publisher_id = db.Column(db.Integer, db.ForeignKey('publisher.id'), nullable=False)
    publisher = relationship("Publisher")
    hidden = db.Column(db.Boolean, nullable=False)
    ebay = relationship("InventoryEbay", uselist=False)
    sale = relationship("InventorySale", uselist=False)

    def groupCreatorsByRole(self):
        grouped = {}
        issue = Issue.query.filter(Issue.item_code==self.issue_id).first()
        if issue:
            if issue.series is not None:
                for c in issue.series.creators:
                    if c.creator_role.name in grouped:
                        grouped[c.creator_role.name].append(c.creator.name)
                    else:
                        grouped[c.creator_role.name] = [c.creator.name]
        return grouped

    def web_formatted_title(self):
        return re.sub(r'(\s#\d*)\s', r'\1<br>', self.title)

    def sale_or_retail_price(self):
        if self.sale:
            return round(self.retail_price * (1 - self.sale.sale_percentage), 2)
        else:
            return self.retail_price

    def web_formatted_sale_or_retail_price(self):
        # not on sale
        if self.sale_or_retail_price()==self.retail_price:
            return self.retail_price
        # on sale
        else:
            return f'{self.sale_or_retail_price()}<i class="fa fa-tag text-success ml-1"></i>'

    def discounted_price(self, discount=1.0):
        return round(self.sale_or_retail_price() * (1 - discount), 2)


class InventoryEbay(db.Model):
    __tablename__ = 'inventory_ebay'
    issue_id = db.Column(db.Integer, db.ForeignKey('inventory.issue_id'), primary_key=True)
    issue = relationship("Inventory")
    ebay_item_id = db.Column(db.Integer, nullable=False)

class InventorySale(db.Model):
    __tablename__ = 'inventory_sale'
    issue_id = db.Column(db.Integer, db.ForeignKey('inventory.issue_id'), primary_key=True)
    issue = relationship("Inventory")
    sale_percentage = db.Column(db.Numeric, nullable=True)


class Issue(db.Model):
    __tablename__ = 'issues'
    title = db.Column(db.String(255), nullable=False)
    item_code = db.Column(db.String(12), primary_key=True)
    series_id=  db.Column(db.Integer, db.ForeignKey('series.id'), nullable=False)
    series = relationship("Series")
    foc_date = db.Column(db.Date, nullable=False)
    est_ship_date = db.Column(db.Date, nullable=False)
    retail_price = db.Column(db.Numeric, nullable=False)
    category_code = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String(), nullable=False)

    def __repr__(self):
        return "Issue(id='%s', title='%s')" % (self.item_code, self.title)

    def web_formatted_title(self):
        return re.sub(r'(\s#\d*)\s', r'\1<br>', self.title)

    def web_formatted_price(self, discount=1.0):
        return f'{round(self.retail_price * discount, 2)} <span class="text-muted" style="text-decoration: line-through;">{self.retail_price}</span>'

    def discounted_price(self, discount=1.0):
        return round(self.retail_price * (1 - discount), 2)


class Order(db.Model):
    __tablename__ = "order"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('user.id'), nullable=False)
    user = relationship("User")
    paypal_order_id = db.Column(db.String(255), nullable=False)
    paypal_email = db.Column(db.String(255), nullable=False)
    subtotal = db.Column(db.Numeric, nullable=False)
    discount = db.Column(db.Numeric, nullable=False)
    shipping = db.Column(db.Numeric, nullable=False)
    total = db.Column(db.Numeric, nullable=False)
    coupon_code = db.Column(db.String(20), nullable=False)
    date = db.Column(db.Date, nullable=False)
    tracking_number = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(255), nullable=False)
    items = relationship("OrderItem")
    address = relationship("OrderShipping", uselist=False)

    def formatted_date(self):
        est = pytz.timezone('US/Eastern')
        return self.date.astimezone(est).strftime("%A, %B %d, %Y at %I:%M %p")

    def compressed_formatted_date(self):
        est = pytz.timezone('US/Eastern')
        return self.date.astimezone(est).strftime("%m/%d/%Y %I:%M %p")


class OrderItem(db.Model):
    __tablename__ = "order_item"
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), primary_key=True)
    order = relationship("Order")
    issue_id = db.Column(db.Integer, db.ForeignKey('inventory.issue_id'), primary_key=True)
    issue = relationship("Inventory")
    units = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric, nullable=False)
    discount_price = db.Column(db.Numeric, nullable=False)
    total_price = db.Column(db.Numeric, nullable=False)


class OrderShipping(db.Model):
    __tablename__ = "order_shipping"
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), primary_key=True)
    order = relationship("Order")
    name = db.Column(db.String(255), nullable=False)
    address_1 = db.Column(db.String(255), nullable=False)
    address_2 = db.Column(db.String(255), nullable=True)
    admin_area_2 = db.Column(db.String(255), nullable=False)
    admin_area_1 = db.Column(db.String(255), nullable=False)
    postal_code = db.Column(db.String(255), nullable=False)
    country_code = db.Column(db.String(255), nullable=False)


class Publisher(db.Model):
    __tablename__ = 'publisher'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    comics = db.Column(db.Boolean, nullable=False)
    trades = db.Column(db.Boolean, nullable=False)
    manga = db.Column(db.Boolean, nullable=False)

    def __repr__(self):
        return 'Publisher %s: %s' % (self.id, self.name)


class Series(db.Model):
    __tablename__ = 'series'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    publisher_id = db.Column(db.Integer, db.ForeignKey('publisher.id'), nullable=False)
    publisher = relationship("Publisher")
    creators = relationship("CreatorSeries")
    item_code = db.Column(db.String(12))


    def groupCreatorsByRole(self):
        grouped = {}
        for c in self.creators:
            if c.creator_role.name in grouped:
                grouped[c.creator_role.name].append(c.creator.name)
            else:
                grouped[c.creator_role.name] = [c.creator.name]
        return grouped

    def __repr__(self):
        return "Series(id='%s', name='%s', publisher_id='%s', artwork_url='%s')" % (self.id, self.name, self.publisher_id, self.artwork_url)


class ShippingMethod(db.Model):
    __tablename__ = 'shipping_method'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), nullable=False)
    delivery_window = db.Column(db.String(20), nullable=False)
    base_price = db.Column(db.Integer)
    incremental_price = db.Column(db.Integer)

    def __repr__(self):
        return "ShippingMethod(id='%s', name='%s', delivery_window='%s', , base_price='%s', , incremental_price='%s')" % (self.id, self.name, self.delivery_window, self.base_price, self.incremental_price)


class ShoppingCart(db.Model):
    __tablename__ = 'shopping_cart'
    user_id = db.Column(db.BigInteger, db.ForeignKey('user.id'), nullable=False)
    user = relationship("User")
    issue_id = db.Column(db.Integer, db.ForeignKey('inventory.issue_id'), primary_key=True)
    inventory = relationship("Inventory")
    units = db.Column(db.Integer)
    created_on = db.Column(db.Date, server_default=db.FetchedValue())

    def web_formatted_total(self, discount=1.0):
        return f'${self.units * round(self.issue.retail_price * discount, 2)}'


class Subscription(db.Model):
    __tablename__ = 'subscriptions'
    user_id = db.Column(db.BigInteger, db.ForeignKey('user.id'), primary_key=True)
    user = relationship("User")
    series_id = db.Column(db.Integer, db.ForeignKey('series.id'), primary_key=True)
    series = relationship("Series")

    def __repr__(self):
        return "Subscription(id='%s', user='%s', series='%s')" % (self.id, self.user.email, self.series.name)

class SubscriptionType(db.Model):
    __tablename__ = 'subscription_type'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(255))

    def __repr__(self):
        return "SubscriptionType(id='%s', name='%s', description='%s')" % (self.id, self.name, self.description)

class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.String, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    active = db.Column(db.Boolean(), default=True)
    anonymous = db.Column(db.Boolean(), default=False)
    admin = db.Column(db.Boolean(), default=False)
    verified = db.Column(db.Boolean(), default=False)

    def __repr__(self):
        return "User(id='%s', email='%s')" % (self.id, self.email)


class UserOrder(db.Model):
    __tablename__ = 'user_order'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('user.id'), nullable=False)
    user = relationship("User")
    issue_id = db.Column(db.Integer, db.ForeignKey('issues.item_code'), nullable=False)
    issue = relationship("Issue")
    units = db.Column(db.Integer)

    def __repr__(self):
        return "UserOrder(issue_id='%s', units='%s')" % (self.issue_id, self.units)


class UserProfile(db.Model):
    __tablename__ = 'user_profile'
    user_id = db.Column(db.String, db.ForeignKey('user.id'), nullable=False, primary_key=True)
    user = relationship("User")
    shipping_frequency = db.Column(db.Integer)
    shipping_method_id = db.Column(db.Integer, db.ForeignKey('shipping_method.id'), nullable=False)
    shipping_method = relationship("ShippingMethod")
    default_subscription_type_id = db.Column(db.Integer, db.ForeignKey('subscription_type.id'), nullable=False)
    default_subscription_type = relationship("SubscriptionType")
    discount_id = db.Column(db.Integer, db.ForeignKey('discount.id'), nullable=False)
    discount = relationship("Discount")

    def __repr__(self):
        return "UserProfile(user_id='%s', frequency='%s', shipping_method='%s', default_subscription_type='%s')" % (self.user_id, self.shipping_frequency, self.shipping_method.name, self.default_subscription_type.name)
