-- Table: user

-- DROP TABLE user;

CREATE TABLE "user"
(
    id character(36) NOT NULL,
    email character varying(120) NOT NULL,
    password character varying(120) NOT NULL,
    active boolean NOT NULL DEFAULT 't',
    anonymous boolean NOT NULL DEFAULT 'f',
    admin boolean NOT NULL DEFAULT 'f',
    verified boolean NOT NULL DEFAULT 'f',
    CONSTRAINT user_pkey PRIMARY KEY (id),
    CONSTRAINT user_email_unique UNIQUE (email)
);

-- Table: user_profile

-- DROP TABLE user_profile;

CREATE TABLE user_profile
(
    user_id character(36) NOT NULL,
    shipping_frequency integer NOT NULL,
    shipping_method_id integer NOT NULL,
    default_subscription_type_id integer NOT NULL,
    discount_id integer NOT NULL,
    CONSTRAINT user_profile_pkey PRIMARY KEY (user_id),
    CONSTRAINT user_profile_discount_id_fk FOREIGN KEY (discount_id)
        REFERENCES discount (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT user_profile_shipping_method_id_fk FOREIGN KEY (shipping_method_id)
        REFERENCES shipping_method (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT user_profile_subscription_type_id_fk FOREIGN KEY (default_subscription_type_id)
        REFERENCES subscription_type (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT user_profile_user_id_fk FOREIGN KEY (user_id)
        REFERENCES "user" (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
);

-- Table: "order"

-- DROP TABLE "order";

CREATE SEQUENCE order_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

CREATE TABLE "order"
(
    id bigint NOT NULL DEFAULT nextval('order_id_seq'::regclass),
    user_id character(36) NOT NULL,
    paypal_order_id character varying(255) NOT NULL,
    paypal_email character varying(255) NOT NULL,
    subtotal numeric NOT NULL,
    discount numeric NOT NULL,
    shipping numeric NOT NULL,
    total numeric NOT NULL,
    coupon_code character varying(20) NOT NULL,
    date timestamp(4) with time zone NOT NULL,
    tracking_number character varying(255),
    status character varying(255),
    CONSTRAINT order_pkey PRIMARY KEY (id)
);

-- Table: order_item

-- DROP TABLE order_item;

CREATE TABLE order_item
(
    order_id integer NOT NULL,
    issue_id character varying(12) NOT NULL,
    units integer NOT NULL,
    unit_price numeric NOT NULL,
    discount_price numeric NOT NULL,
    total_price numeric NOT NULL,
    CONSTRAINT order_item_pk PRIMARY KEY (order_id, issue_id),
    CONSTRAINT order_issue_id_fk FOREIGN KEY (issue_id)
        REFERENCES issues (item_code) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT order_item_order_id_fk FOREIGN KEY (order_id)
        REFERENCES "order" (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
);

-- Table: order_shipping

-- DROP TABLE order_shipping;

CREATE TABLE order_shipping
(
    order_id bigint NOT NULL,
    name character varying(255) NOT NULL,
    address_1 character varying(255) NOT NULL,
    address_2 character varying(255),
    admin_area_2 character varying(255) NOT NULL,
    admin_area_1 character varying(255) NOT NULL,
    postal_code character varying(255) NOT NULL,
    country_code character varying(255) NOT NULL,
    CONSTRAINT order_id_unique UNIQUE (order_id),
    CONSTRAINT order_id_fk FOREIGN KEY (order_id)
        REFERENCES "order" (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
);

-- Table: shopping_cart

-- DROP TABLE shopping_cart;

CREATE TABLE shopping_cart
(
    user_id character(36) NOT NULL,
    issue_id character varying(12) NOT NULL,
    units integer NOT NULL,
    created_on date NOT NULL default CURRENT_DATE,
    CONSTRAINT shopping_cart_user_issue_unique UNIQUE (user_id, issue_id),
    CONSTRAINT shopping_cart_issue_id_fk FOREIGN KEY (issue_id)
        REFERENCES inventory (issue_id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
);

-- Table: user_order

-- DROP TABLE user_order;

CREATE SEQUENCE user_order_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

CREATE TABLE user_order
(
    id bigint NOT NULL DEFAULT nextval('user_order_id_seq'::regclass),
    user_id character(36) NOT NULL,
    issue_id character varying(12) NOT NULL,
    units integer NOT NULL,
    CONSTRAINT user_order_pkey PRIMARY KEY (id),
    CONSTRAINT user_order_issue_id_fk FOREIGN KEY (issue_id)
        REFERENCES issues (item_code) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT user_order_user_id_fk FOREIGN KEY (user_id)
        REFERENCES "user" (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
);

-- Table: subscriptions

-- DROP TABLE subscriptions;

CREATE TABLE subscriptions
(
  user_id character(36) NOT NULL,
  series_id integer NOT NULL,
  CONSTRAINT subscriptions_user_series_unique UNIQUE (user_id, series_id),
  CONSTRAINT subscriptions_user_id_fk FOREIGN KEY (user_id)
      REFERENCES "user" (id) MATCH SIMPLE
      ON UPDATE NO ACTION
      ON DELETE NO ACTION
);
