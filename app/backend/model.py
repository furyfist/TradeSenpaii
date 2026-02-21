from pydantic import BaseModel
from typing import Optional

class PredictionResponse(BaseModel):
    ticker:             str
    prediction:         str        # "UP" or "DOWN"
    confidence:         float      # 0.0 to 1.0
    predicted_date:     str        # date being predicted
    as_of_date:         str        # last known trading day
    top_signals:        list[dict] # feature name + value + direction
    sentiment_score:    float
    sentiment_label:    str
    model_accuracy:     float

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
    date:              str
    lm_sentiment_score: float
    lm_neg_pct:        float
    lm_uncertain_pct:  float
    form_type:         str

class SentimentHistoryResponse(BaseModel):
    ticker: str
    data:   list[SentimentPoint]

class ModelInfoResponse(BaseModel):
    ticker:          str
    cv_accuracy:     float
    trained_on:      str
    input_features:  int
    sequence_len:    int
    model_type:      str
    last_updated:    str