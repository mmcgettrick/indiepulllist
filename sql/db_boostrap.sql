-- create tables
-- run create_tables.sql
-- run create_user_tables.sql

-- populate support tables
INSERT INTO shipping_method (name, delivery_window, base_price, incremental_price)
VALUES
('USPS Media Mail','2-8 Business Days','3.50','1.00'),
('USPS Priority Mail','1-2 Business Days','7.95','1.00');

INSERT INTO subscription_type (name, description)
VALUES
('A Covers','Send me the only the primary covers, do not send cover variants.'),
('A Covers + Variants','In addition to primary covers, please send all available variant covers (*excludes incentive covers)'),
('A Covers + Trades','Send me primary covers and Trades.'),
('Trades Only','Only send me Trade Paperbacks for this series, no single issues.'),
('Everything','Send me all issues, variants, and trades for this series! (*excludes incentive covers)');

INSERT INTO discount (name, percentage)
VALUES
('Store Discount', 0.90),
('Subscriber Discount', 0.80),
('Employee Discount', 0.70);

-- Set Creator Roles
INSERT INTO creator_role (name) VALUES
('Writer'),
('Artist'),
('Colorist');

-- run load_master_data.py

-- run load_publisher.py
-- "Image Comics" "Vault Comics" "Dark Horse Comics" "Boom! Studios" "Archie Comic Publications" "Valiant Entertainment LLC" "IDW Publishing" "Titan Comics" "Oni Press Inc." "Aftershock Comics"

-- run load_artwork.py

-- CREATOR: load writers
INSERT INTO creator (name)
SELECT DISTINCT(a.name) FROM (
	SELECT (substring("WRITER" from ',(.*?)$') || ' ' || substring("WRITER" from '^(.*?),')) as name
	FROM dmd_master_data
	WHERE "CATEGORY" = '1'
	AND "SERIES_CODE" != '0'
) as a
WHERE a.name is not null
ORDER BY a.name
ON CONFLICT (name)
DO NOTHING;

-- CREATOR: load artists
INSERT INTO creator (name)
SELECT DISTINCT(a.name) FROM (
	SELECT (substring("ARTIST" from ',(.*?)$') || ' ' || substring("ARTIST" from '^(.*?),')) as name
	FROM dmd_master_data
	WHERE "CATEGORY" = '1'
	AND "SERIES_CODE" != '0'
) as a
WHERE a.name is not null
ORDER BY a.name
ON CONFLICT (name)
DO NOTHING;

-- CREATOR: load colorists
INSERT INTO creator (name)
SELECT DISTINCT(a.name) FROM (
	SELECT (substring("COLORIST" from ',(.*?)$') || ' ' || substring("COLORIST" from '^(.*?),')) as name
	FROM dmd_master_data
	WHERE "CATEGORY" = '1'
	AND "SERIES_CODE" != '0'
) as a
WHERE a.name is not null
ORDER BY a.name
ON CONFLICT (name)
DO NOTHING;

-- load_series.py
-- "Image Comics" "Vault Comics" "Dark Horse Comics" "Boom! Studios" "Archie Comic Publications" "Valiant Entertainment LLC" "IDW Publishing" "Titan Comics" "Oni Press Inc." "Aftershock Comics"

-- load_issues.py
-- "Image Comics" "Vault Comics" "Dark Horse Comics" "Boom! Studios" "Archie Comic Publications" "Valiant Entertainment LLC" "IDW Publishing" "Titan Comics" "Oni Press Inc." "Aftershock Comics"


-- CREATOR_SERIES: Populate Writers
INSERT INTO creator_series (creator_id, creator_role_id, series_id)
SELECT d.id as creator_id, c.id as role_id, a.series_id FROM (
	SELECT DISTINCT ON (writer, series_id) (substring("WRITER" from ',(.*?)$') || ' ' || substring("WRITER" from '^(.*?),')) as writer, CAST("SERIES_CODE" as Integer) as series_id, 'Writer' as role
	FROM dmd_master_data
	WHERE "CATEGORY" = '1'
	AND "SERIES_CODE" != '0'
) as a
INNER JOIN series AS b ON a.series_id = b.id --limit to only active series
INNER JOIN creator_role AS c ON a.role = c.name --lookup role id
INNER JOIN creator AS d ON d.name = a.writer --lookup creator id
ON CONFLICT (creator_id, creator_role_id, series_id)
DO NOTHING;

-- CREATOR_SERIES: Populate Artists
INSERT INTO creator_series (creator_id, creator_role_id, series_id)
SELECT d.id as creator_id, c.id as role_id, a.series_id FROM (
	SELECT DISTINCT ON (artist, series_id) (substring("ARTIST" from ',(.*?)$') || ' ' || substring("ARTIST" from '^(.*?),')) as artist, CAST("SERIES_CODE" as Integer) as series_id, 'Artist' as role
	FROM dmd_master_data
	WHERE "CATEGORY" = '1'
	AND "SERIES_CODE" != '0'
) as a
INNER JOIN series AS b ON a.series_id = b.id --limit to only active series
INNER JOIN creator_role AS c ON a.role = c.name --lookup role id
INNER JOIN creator AS d ON d.name = a.artist --lookup creator id
ON CONFLICT (creator_id, creator_role_id, series_id)
DO NOTHING;

-- CREATOR_SERIES: Populate Colorists
INSERT INTO creator_series (creator_id, creator_role_id, series_id)
SELECT d.id as creator_id, c.id as role_id, a.series_id FROM (
	SELECT DISTINCT ON (colorist, series_id) (substring("COLORIST" from ',(.*?)$') || ' ' || substring("COLORIST" from '^(.*?),')) as colorist, CAST("SERIES_CODE" as Integer) as series_id, 'Colorist' as role
	FROM dmd_master_data
	WHERE "CATEGORY" = '1'
	AND "SERIES_CODE" != '0'
) as a
INNER JOIN series AS b ON a.series_id = b.id --limit to only active series
INNER JOIN creator_role AS c ON a.role = c.name --lookup role id
INNER JOIN creator AS d ON d.name = a.colorist --lookup creator id
ON CONFLICT (creator_id, creator_role_id, series_id)
DO NOTHING;
