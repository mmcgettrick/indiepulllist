from flask_wtf import FlaskForm
from sqlalchemy import desc, distinct
from wtforms import BooleanField, DateField, DecimalField, FieldList, FormField, HiddenField, IntegerField, SelectField, StringField, PasswordField, SubmitField
from wtforms.widgets import CheckboxInput, HiddenInput, ListWidget
from wtforms.validators import DataRequired, Email, Length, EqualTo, NumberRange
from wtforms_sqlalchemy.fields import QuerySelectField, QuerySelectMultipleField
from subscriptions.models import Inventory, Publisher


class AddToShoppingCartForm(FlaskForm):
    issue_id = StringField(widget=HiddenInput())
    units = IntegerField(widget=HiddenInput())
    submit = SubmitField("Add To Cart")


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField("Current Password", validators=[DataRequired(), Length(min=6, max=120)])
    new_password = PasswordField("New Password", validators=[DataRequired(), Length(min=8, max=120)])
    new_password_confirm = PasswordField("Confirm New Password", validators=[DataRequired(), Length(min=8, max=120), EqualTo('new_password')])
    submit = SubmitField("Change Password")


class InventoryItemForm(FlaskForm):
    issue_id = StringField("Issue ID", validators=[DataRequired(), Length(min=1, max=12)])
    title = StringField("Title", validators=[DataRequired(), Length(min=1, max=255)])
    publisher = QuerySelectField(
        'Publisher',
        query_factory=lambda: Publisher.query.order_by(Publisher.name).all(),
        get_label='name',
        get_pk=lambda x: x.id
    )
    units = IntegerField("Units", validators=[DataRequired(), NumberRange(min=0)])
    retail_price = DecimalField("Retail Price")
    release_date = DateField("Release Date", format='%Y-%m-%d', validators=[DataRequired()])
    sale = DecimalField("Sale")
    hidden = BooleanField("Hidden")
    ebay_item_id = StringField("eBay Item ID")
    submit = SubmitField("Add")


class IssueUnitForm(FlaskForm):
    issue_id = IntegerField("IssueId")
    units = SelectField(u'Units',
        choices=[('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5')])
    selected = BooleanField("Selected")
    submit = SubmitField("Save Changes")


class IssueOrderForm(FlaskForm):
    user_id = HiddenField(validators=[DataRequired()])
    orders = FieldList(FormField(IssueUnitForm))
    submit = SubmitField("Save Changes")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email(), Length(min=6, max=120)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6, max=120)])
    submit = SubmitField("Login")


class MangaSearchForm(FlaskForm):
    search = StringField("Search", validators=[DataRequired()])
    publishers = QuerySelectField(
        'Publisher',
        query_factory=lambda: Publisher.query.filter(Publisher.name!='DC Comics').filter(Publisher.name!='Marvel Comics').filter(Publisher.manga==True).order_by(Publisher.name).all(),
        get_label='name',
        get_pk=lambda x: x.id,
        allow_blank=True,
        blank_text=u'All Publishers'
    )
    sort_by = SelectField(
        u'Sort By',
        choices=[
            ('newest', 'Newest > Title'),
            ('title_az', 'Title > Newest'),
            ('publisher_newest', 'Publisher > Newest > Title'),
            ('publisher_az', 'Publisher > Title > Newest')
        ]
    )
    on_sale = BooleanField("On Sale?")
    submit = SubmitField("Search")


class ProfileForm(FlaskForm):
    submit = SubmitField("Save")


class RegisterForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email(), Length(min=6, max=120)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8, max=120)])
    password_confirm = PasswordField("Confirm Password", validators=[DataRequired(), Length(min=8, max=120), EqualTo('password')])
    submit = SubmitField("Register")


class SearchInventoryForm(FlaskForm):
    search = StringField("Search", validators=[])
    publishers = QuerySelectField(
        'Publisher',
        query_factory=lambda: Publisher.query.order_by(Publisher.name).all(),
        get_label='name',
        get_pk=lambda x: x.id,
        allow_blank=True,
        blank_text=u'All Publishers'
    )
    release_date = QuerySelectField(
        'Release Date',
        query_factory=lambda: Inventory.query.distinct(Inventory.release_date).order_by(desc(Inventory.release_date)).all(),
        get_label='release_date',
        get_pk=lambda x: x.release_date,
        allow_blank=True,
        blank_text=u'All'
    )
    only_show_visible = BooleanField("Shows In Store", default=True)
    inventory = FieldList(FormField(InventoryItemForm))
    submit = SubmitField("Apply")


class SeriesFilterForm(FlaskForm):
    publishers = QuerySelectField(
        'Publisher',
        query_factory=lambda: Publisher.query.order_by(Publisher.name).all(),
        get_label='name',
        get_pk=lambda x: x.id,
        allow_blank=True,
        blank_text=u'All Publishers'
    )
    series = StringField("Series", validators=[])
    submit = SubmitField("Apply")

class SeriesSearchForm(FlaskForm):
    search = StringField("Search", validators=[DataRequired()])
    publishers = QuerySelectField(
        'Publisher',
        #query_factory=lambda: Publisher.query.filter(Publisher.name!='DC Comics').filter(Publisher.name!='Marvel Comics').order_by(Publisher.name).all(),
        query_factory=lambda: Publisher.query.order_by(Publisher.name).all(),
        get_label='name',
        get_pk=lambda x: x.id,
        allow_blank=True,
        blank_text=u'All Publishers'
    )
    submit = SubmitField("Search")


class ShoppingCartItemForm(FlaskForm):
    user_id = HiddenField(validators=[DataRequired()])
    issue_id = HiddenField(validators=[DataRequired()])
    units = IntegerField(widget=HiddenInput())
    remove = IntegerField(widget=HiddenInput(), default="0", validators=[DataRequired()])
    submit = SubmitField("Submit")


class StoreFilterAndSortForm(FlaskForm):
    publishers = QuerySelectMultipleField(
        'Publisher',
        query_factory=lambda: Publisher.query.order_by(Publisher.name).all(),
        widget=ListWidget(prefix_label=False),
        option_widget=CheckboxInput(),
        get_label='name',
        get_pk=lambda x: x.id
    )
    sort_by = SelectField(u'Sort By', choices=[('', 'Most Recent'), ('', 'Title (A-Z)')])
    submit = SubmitField("Apply")


class StoreSearchForm(FlaskForm):
    search = StringField("Search", validators=[DataRequired()])
    publishers = QuerySelectField(
        'Publisher',
        query_factory=lambda: Publisher.query.filter(Publisher.name!='DC Comics').filter(Publisher.name!='Marvel Comics').filter(Publisher.comics==True).order_by(Publisher.name).all(),
        get_label='name',
        get_pk=lambda x: x.id,
        allow_blank=True,
        blank_text=u'All Publishers'
    )
    sort_by = SelectField(
        u'Sort By',
        choices=[
            ('newest', 'Newest > Title'),
            ('title_az', 'Title > Newest'),
            ('publisher_newest', 'Publisher > Newest > Title'),
            ('publisher_az', 'Publisher > Title > Newest')
        ]
    )
    on_sale = BooleanField("On Sale?")
    submit = SubmitField("Search")


class UpdateCouponCodeForm(FlaskForm):
    coupon_code = StringField("Coupon Code")
    submit = SubmitField("Apply")


class UpdateInventoryForm(FlaskForm):
    issue_id = StringField(widget=HiddenInput())
    units = IntegerField("Units", validators=[DataRequired(), NumberRange(min=0)])
    release_date = DateField("Release Date", format='%Y-%m-%d', validators=[DataRequired()])
    hidden = BooleanField("Hidden")
    submit = SubmitField("Update")


class UpdateShippingMethodForm(FlaskForm):
    shipping_method_id = IntegerField(widget=HiddenInput())
    submit = SubmitField("Update Shipping Method")
