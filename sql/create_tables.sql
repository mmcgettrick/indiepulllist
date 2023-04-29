
-- Table: dmd_master_data

-- DROP TABLE dmd_master_data;

CREATE TABLE dmd_master_data
(
    "DIAMD_NO" text,
    "STOCK_NO" text,
    "PARENT_ITEM_NO_ALT" text,
    "BOUNCE_USE_ITEM" text,
    "FULL_TITLE" text,
    "MAIN_DESC" text,
    "VARIANT_DESC" text,
    "SERIES_CODE" text,
    "ISSUE_NO" text,
    "ISSUE_SEQ_NO" text,
    "VOLUME_TAG" text,
    "MAX_ISSUE" text,
    "PRICE" text,
    "PUBLISHER" text,
    "UPC_NO" text,
    "SHORT_ISBN_NO" text,
    "EAN_NO" text,
    "CARDS_PER_PACK" text,
    "PACK_PER_BOX" text,
    "BOX_PER_CASE" text,
    "DISCOUNT_CODE" text,
    "INCREMENT" text,
    "PRNT_DATE" text,
    "FOC_VENDOR" text,
    "SHIP_DATE" text,
    "SRP" text,
    "CATEGORY" text,
    "GENRE" text,
    "BRAND_CODE" text,
    "MATURE" text,
    "ADULT" text,
    "OA" text,
    "CAUT1" text,
    "CAUT2" text,
    "CAUT3" text,
    "RESOL" text,
    "NOTE_PRICE" text,
    "ORDER_FORM_NOTES" text,
    "PAGE" text,
    "WRITER" text,
    "ARTIST" text,
    "COVER_ARTIST" text,
    "COLORIST" text,
    "ALLIANCE_SKU" text,
    "FOC_DATE" text,
    "OFFERED_DATE" text,
    "NUMBER_OF_PAGES" text
);

-- Table: public.previews

-- DROP TABLE public.previews;

CREATE TABLE public.previews
(
    item_code text,
    title text,
    srp double precision,
    description text
)

-- Table: item_code_stock_xref

-- DROP TABLE item_code_stock_xref;

CREATE TABLE item_code_stock_xref
(
    item_code character varying(10)  NOT NULL,
    stock_number character varying(10)  NOT NULL,
    CONSTRAINT item_code_stock_xref_pkey PRIMARY KEY (item_code),
    CONSTRAINT icsx_item_code_stock_number_unique UNIQUE (item_code, stock_number)
);

CREATE SEQUENCE blog_id_seq
    INCREMENT 1
    START 5
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

CREATE TABLE blog
(
    id bigint NOT NULL DEFAULT nextval('blog_id_seq'::regclass),
    author character varying(255) NOT NULL,
    date timestamp with time zone NOT NULL DEFAULT now(),
    title character varying(255) NOT NULL,
    text text NOT NULL,
    store_link character varying(255),
    CONSTRAINT blog_pkey PRIMARY KEY (id)
)


-- Table: creator

-- DROP TABLE creator;
CREATE SEQUENCE creator_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

CREATE TABLE creator
(
    id bigint NOT NULL DEFAULT nextval('creator_id_seq'::regclass),
    name character varying(255)  NOT NULL,
    CONSTRAINT creator_pkey PRIMARY KEY (id),
    CONSTRAINT creator_name_unique UNIQUE (name)

);

-- Table: creator_role

-- DROP TABLE creator_role;
CREATE SEQUENCE creator_role_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

CREATE TABLE creator_role
(
    id bigint NOT NULL DEFAULT nextval('creator_role_id_seq'::regclass),
    name character varying(255)  NOT NULL,
    CONSTRAINT creator_role_pkey PRIMARY KEY (id)
);

-- Table: creator_series

-- DROP TABLE creator_series;
CREATE SEQUENCE creator_series_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

CREATE TABLE creator_series
(
    id bigint NOT NULL DEFAULT nextval('creator_series_id_seq'::regclass),
    creator_id integer NOT NULL,
    creator_role_id integer NOT NULL,
    series_id integer NOT NULL,
    CONSTRAINT creator_series_pkey PRIMARY KEY (id),
    CONSTRAINT creator_role_series_unk UNIQUE (creator_id, creator_role_id, series_id),
    CONSTRAINT creator_series_creator_id_fk FOREIGN KEY (creator_id)
        REFERENCES creator (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    CONSTRAINT creator_series_creator_role_id_fk FOREIGN KEY (creator_role_id)
        REFERENCES creator_role (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
);

-- Table: discount

-- DROP TABLE discount;

CREATE SEQUENCE discounts_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

CREATE TABLE discount
(
    id bigint NOT NULL DEFAULT nextval('discounts_id_seq'::regclass),
    name character varying  NOT NULL,
    percentage numeric NOT NULL,
    code character varying  NOT NULL,
    CONSTRAINT discounts_pkey PRIMARY KEY (id)
);

CREATE TABLE ebay_sales
(
    item_id bigint NOT NULL,
    buyer_email character varying(255) NOT NULL,
    buyer_zipcode character varying(20) NOT NULL,
    item_code character varying(12),
    listing_start_time timestamp with time zone NOT NULL,
    listing_end_time timestamp with time zone NOT NULL,
    title character varying(255) NOT NULL,
    quantity integer NOT NULL,
    subtotal numeric NOT NULL,
    transaction_id character varying(255) NOT NULL,
    order_id character varying(255),
    CONSTRAINT item__buyer_time_unique UNIQUE (item_id, buyer_email, listing_end_time)
);

-- Table: invoice

-- DROP TABLE invoice;

CREATE TABLE invoice
(
    units_shipped bigint,
    item_code text ,
    discount_code text ,
    item_description text ,
    retail_price numeric(8,3),
    unit_price numeric(8,3),
    invoice_amount numeric(8,3),
    category_code bigint,
    order_type bigint,
    processed_as text ,
    order_number bigint,
    upc_code text ,
    isbn_code text ,
    ean_code text ,
    po_number text ,
    allocated_code bigint,
    publisher text ,
    series_code bigint,
    date date
);

-- Table: issues

-- DROP TABLE issues;

CREATE TABLE issues
(
    title character varying(255)  NOT NULL,
    item_code character varying(12)  NOT NULL,
    series_id integer NOT NULL,
    foc_date date NOT NULL,
    est_ship_date date NOT NULL,
    retail_price numeric NOT NULL,
    category_code integer NOT NULL,
    issue_number integer NOT NULL,
    variant boolean NOT NULL,
    description text,
    CONSTRAINT issues_item_code_unique UNIQUE (item_code)

);

-- Table: inventory

-- DROP TABLE inventory;

CREATE TABLE inventory
(
    issue_id character varying(12)  NOT NULL,
    units integer NOT NULL,
    release_date date NOT NULL,
    hidden boolean NOT NULL DEFAULT true,
    title character varying(255) NOT NULL,
    description text,
    retail_price numeric NOT NULL,
    publisher_id integer NOT NULL,
    CONSTRAINT inventory_issue_id_unique UNIQUE (issue_id),
    CONSTRAINT inventory_publisher_id_fk FOREIGN KEY (publisher_id)
        REFERENCES publisher (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
);

-- Table: inventory_ebay

-- DROP TABLE inventory_ebay;

CREATE TABLE inventory_ebay
(
    issue_id character varying(12) NOT NULL,
    ebay_item_id bigint NOT NULL,
    CONSTRAINT inventory_ebay_pk PRIMARY KEY (issue_id),
    CONSTRAINT inventory_issue_id_fk FOREIGN KEY (issue_id)
        REFERENCES inventory (issue_id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
);

-- Table: public.inventory_sale

-- DROP TABLE public.inventory_sale;

CREATE TABLE inventory_sale
(
    issue_id character varying(12) NOT NULL,
    sale_percentage numeric NOT NULL,
    CONSTRAINT inventory_sale_pk PRIMARY KEY (issue_id),
    CONSTRAINT inventory_issue_id_fk FOREIGN KEY (issue_id)
        REFERENCES inventory (issue_id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
);

-- Table: publisher

-- DROP TABLE publisher;

CREATE SEQUENCE publisher_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

CREATE TABLE publisher
(
    id bigint NOT NULL DEFAULT nextval('publisher_id_seq'::regclass),
    name character varying(255)  NOT NULL,
    CONSTRAINT publisher_pkey PRIMARY KEY (id),
    CONSTRAINT publisher_name_unique UNIQUE (name)
);

-- Table: series

-- DROP TABLE series;

CREATE TABLE series
(
    id bigint NOT NULL,
    name character varying(255)  NOT NULL,
    publisher_id integer NOT NULL,
    artwork_url character varying(255),
    CONSTRAINT series_id_pk PRIMARY KEY (id),
    CONSTRAINT series_publisher_id_fk FOREIGN KEY (publisher_id)
        REFERENCES publisher (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
);

-- Table: shipping_method

-- DROP TABLE shipping_method;
CREATE SEQUENCE shipping_method_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

CREATE TABLE shipping_method
(
    id bigint NOT NULL DEFAULT nextval('shipping_method_id_seq'::regclass),
    name character varying(20)  NOT NULL,
    delivery_window character varying(20)  NOT NULL,
    base_price numeric NOT NULL,
    incremental_price numeric NOT NULL,
    CONSTRAINT shipping_method_pkey PRIMARY KEY (id)
);

-- Table: subscription_type

-- DROP TABLE subscription_type;

CREATE SEQUENCE subscription_types_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

CREATE TABLE subscription_type
(
    id bigint NOT NULL DEFAULT nextval('subscription_types_id_seq'::regclass),
    name character varying(20)  NOT NULL,
    description character varying(255) ,
    CONSTRAINT subscription_type_pkey PRIMARY KEY (id)
);
