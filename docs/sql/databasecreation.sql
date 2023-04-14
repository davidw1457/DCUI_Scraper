USE dcui;

DROP TABLE series;
DROP TABLE issues;
DROP TABLE creators;
DROP TABLE issue_creators;
DROP VIEW series_date;

CREATE TABLE series
(
	series_id		INT unsigned NOT NULL AUTO_INCREMENT,
    series_title	VARCHAR(255) NOT NULL,
    issue_count		SMALLINT,
    series_url		VARCHAR(255) NOT NULL,
    need_update		TINYINT DEFAULT 1,
    date_updated	DATE,
    PRIMARY KEY (series_id)
);

CREATE TABLE issues
(
	series_id			INT unsigned NOT NULL,
    issue_id			INT unsigned NOT NULL AUTO_INCREMENT,
    issue_title			VARCHAR(255) NOT NULL,
    publication_date	DATE,
    issue_url			VARCHAR(255) NOT NULL,
    PRIMARY KEY (issue_id)
);

CREATE TABLE creators
(
	creator_id		INT unsigned NOT NULL AUTO_INCREMENT,
    creator_name	VARCHAR(255) NOT NULL,
    PRIMARY KEY (creator_id)
);

CREATE TABLE issue_creators
(
	issue_id	INT unsigned NOT NULL,
    creator_id	INT unsigned NOT NULL
);

CREATE VIEW series_date AS
    SELECT 
        series.series_title,
        series.series_id,
        MIN(issues.publication_date) AS earliest_date,
        MAX(issues.publication_date) AS latest_date,
		COUNT(issues.issue_id) AS issues,
        MAX(series.issue_count) AS expected_issues
    FROM
        issues
            INNER JOIN
        series ON issues.series_id = series.series_id
    GROUP BY series.series_title, series.series_id;