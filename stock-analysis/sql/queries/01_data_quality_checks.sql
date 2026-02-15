-- Purpose: Verify the data integrity before analysis:)

-- check 1: record count and date range
SELECT
		COUNT(*) as total_records,
		MIN(date) as earliest_date,
		MAX(date) as latest_date,
		MAX(date) - MIN(date) as days_covered
FROM coca_cola_stock;
-- the differce in total days and records available is due to the non-trading days (sundays + hoidays)

-- check 2: Missing Values
SELECT 
	COUNT (*) as total_rows,
	COUNT (date) as date_count,
	COUNT (close) as close_count,
	COUNT (open) as open_count,
	COUNT (high) as high_count,
	COUNT (low) as low_count,
	COUNT (volume) as volume_count,
	COUNT(*) - COUNT(close) as missing_close,
    COUNT(*) - COUNT(volume) as missing_volume
FROM coca_cola_stock;

-- check 3: Data Anomalies (-ve price, zero volume)
SELECT 
	date, open, high,low,close,volume
FROM coca_cola_stock
WHERE close <= 0
	OR high < low
	OR high < close
	OR low > close
	or Volume = 0
ORDER BY date DESC;

-- check 4: Duplicate dates
SELECT
	date,
	COUNT(*) as occurence_count
FROM coca_cola_stock
GROUP BY date
HAVING COUNT(*) > 1;

-- check 5: Trading days gaps(weekends are normal, but large gaps are suspicious)
WITH date_gaps AS (
	SELECT
		date,
		LAG(date) OVER (ORDER BY date) as prev_date,
		date - LAG(date) OVER (ORDER BY date)as gap_days
	FROM coca_cola_stock
)
SELECT 
	prev_date,
	date,
	gap_days
FROM date_gaps
WHERE gap_days > 7 -- more than a week off
ORDER BY gap_days DESC
LIMIT 20;