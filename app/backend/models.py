from pydantic import BaseModel

SUPPORTED_TICKERS = ["KO", "JNJ", "PG", "WMT", "AAPL", "GOOGL"]

class PredictionResponse(BaseModel):
    ticker:          str
    name:            str
    prediction:      str
    confidence:      float
    predicted_date:  str
    as_of_date:      str
    top_signals:     list[dict]
    sentiment_score: float
    sentiment_label: str
    model_accuracy:  float

class PricePoint(BaseModel):
    date:   str
    open:   float
    high:   float
    low:    float
    close:  float
    volume: float

class PriceHistoryResponse(BaseModel):
    ticker: str
    data:   list[PricePoint]

class SentimentPoint(BaseModel):
    date:               str
    lm_sentiment_score: float
    lm_neg_pct:         float
    lm_uncertain_pct:   float
    form_type:          str

class SentimentHistoryResponse(BaseModel):
    ticker: str
    data:   list[SentimentPoint]

class ModelInfoResponse(BaseModel):
    ticker:         str
    name:           str
    sector:         str
    cv_accuracy:    float
    trained_on:     str
    input_features: int
    sequence_len:   int
    model_type:     str
    last_updated:   str