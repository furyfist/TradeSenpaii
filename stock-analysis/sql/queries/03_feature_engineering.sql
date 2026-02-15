-- Purpose: Calculate technical indicators as features

-- First, define rsi_calculation CTE
WITH rsi_calculation AS (
    SELECT 
        date,
        close,
        -- Calculate gains and losses for RSI
        CASE 
            WHEN (close - LAG(close) OVER (ORDER BY date)) > 0 
            THEN (close - LAG(close) OVER (ORDER BY date)) 
            ELSE 0 
        END as gain,
        CASE 
            WHEN (close - LAG(close) OVER (ORDER BY date)) < 0 
            THEN ABS(close - LAG(close) OVER (ORDER BY date)) 
            ELSE 0 
        END as loss
    FROM coca_cola_stock
),

-- Master Feature Table (This will be my training data)
base_data AS (
    SELECT
        date,
        open,
        high,
        low,
        close,
        volume,
        -- daily returns
        ROUND(((close - LAG(close) OVER (ORDER BY date)) /
            NULLIF(LAG(close) OVER (ORDER BY date), 0) * 100)::numeric, 4) as daily_return,
        -- Price gaps
        ROUND(((open - LAG(close) OVER (ORDER BY date)) /
            NULLIF(LAG(close) OVER (ORDER BY date), 0) * 100)::numeric, 4) as gap_pct,
        -- Lagged prices (past values as features)
        LAG(close, 1) OVER (ORDER BY date) as close_lag1,
        LAG(close, 5) OVER (ORDER BY date) as close_lag5,
        LAG(close, 10) OVER (ORDER BY date) as close_lag10,
        -- Moving averages
        ROUND(AVG(close) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)::numeric, 2) as MA_7,
        ROUND(AVG(close) OVER (ORDER BY date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW)::numeric, 2) as MA_20,
        ROUND(AVG(close) OVER (ORDER BY date ROWS BETWEEN 49 PRECEDING AND CURRENT ROW)::numeric, 2) as MA_50,
        ROUND(AVG(close) OVER (ORDER BY date ROWS BETWEEN 199 PRECEDING AND CURRENT ROW)::numeric, 2) as MA_200,
        -- Volatility (rolling standard deviation)
        ROUND(STDDEV(close) OVER (ORDER BY date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW)::numeric, 4) as volatility_20,
        ROUND(STDDEV(close) OVER (ORDER BY date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW)::numeric, 4) as volatility_30,
        -- volume metrics
        ROUND(AVG(volume) OVER (ORDER BY date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW)::numeric, 0) as avg_volume_20,
        ROUND((volume::numeric / NULLIF(AVG(volume) OVER (ORDER BY date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW), 0))::numeric, 2) as volume_ratio_20
    FROM coca_cola_stock
),

momentum_features AS (
    SELECT 
        *,
        -- price momentum (5 days and 10 days)
        ROUND(((close - close_lag5) / NULLIF(close_lag5, 0) * 100)::numeric, 2) as momentum_5d,
        ROUND(((close - close_lag10) / NULLIF(close_lag10, 0) * 100)::numeric, 2) as momentum_10d,
        -- Distance from moving averages
        ROUND(((close - MA_20) / NULLIF(MA_20, 0) * 100)::numeric, 2) as distance_from_MA20,
        ROUND(((close - MA_50) / NULLIF(MA_50, 0) * 100)::numeric, 2) as distance_from_MA50,
        -- Bollinger Bands
        ROUND((MA_20 + 2 * volatility_20)::numeric, 2) as upper_band_20,
        ROUND((MA_20 - 2 * volatility_20)::numeric, 2) as lower_band_20
    FROM base_data
),

rsi_features AS (
    SELECT 
        date,
        close,
        ROUND((100 - (100 / (1 + NULLIF(
            AVG(gain) OVER (ORDER BY date ROWS BETWEEN 13 PRECEDING AND CURRENT ROW) / 
            NULLIF(AVG(loss) OVER (ORDER BY date ROWS BETWEEN 13 PRECEDING AND CURRENT ROW), 0)
        , 0))))::numeric, 2) as RSI_14
    FROM rsi_calculation
)

-- Final combined feature table
SELECT 
    m.*,
    r.RSI_14,
    
    -- Market regime indicator
    CASE 
        WHEN m.close > m.MA_200 THEN 'Bull'
        WHEN m.close < m.MA_200 THEN 'Bear'
        ELSE 'Neutral'
    END as market_regime,
    
    -- Temporal features
    EXTRACT(DOW FROM m.date) as day_of_week,  -- 0=Sunday, 6=Saturday
    EXTRACT(MONTH FROM m.date) as month,
    EXTRACT(QUARTER FROM m.date) as quarter,
    
    -- Target variable (what we want to predict!)
    LEAD(m.close) OVER (ORDER BY m.date) as next_day_close,
    ROUND(((LEAD(m.close) OVER (ORDER BY m.date) - m.close) / NULLIF(m.close, 0) * 100)::numeric, 4) as next_day_return,
    CASE 
        WHEN LEAD(m.close) OVER (ORDER BY m.date) > m.close THEN 1 
        ELSE 0 
    END as target_direction  -- 1 = UP, 0 = DOWN
    
FROM momentum_features m
LEFT JOIN rsi_features r ON m.date = r.date
WHERE m.date >= '1963-01-01'  -- Remove first year due to MA_200 calculation
ORDER BY m.date;