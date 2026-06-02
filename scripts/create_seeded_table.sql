-- Run once in Supabase SQL editor before running seed_predictions.py

CREATE TABLE IF NOT EXISTS seeded_predictions (
    ticker          TEXT PRIMARY KEY,
    name            TEXT,
    prediction      TEXT,
    confidence      FLOAT,
    predicted_date  TEXT,
    as_of_date      TEXT,
    top_signals     JSONB,
    sentiment_score FLOAT,
    sentiment_label TEXT,
    model_accuracy  FLOAT,
    sector          TEXT,
    input_features  INT,
    sequence_len    INT,
    model_type      TEXT,
    trained_on      TEXT,
    cv_accuracy     FLOAT
);
