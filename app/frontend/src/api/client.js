import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:8000",
  timeout: 30000,
});

export const fetchPrediction       = (ticker) => api.get(`/predict?ticker=${ticker}`);
export const fetchPriceHistory     = (ticker) => api.get(`/price-history?ticker=${ticker}`);
export const fetchSentimentHistory = (ticker) => api.get(`/sentiment-history?ticker=${ticker}`);
export const fetchModelInfo        = (ticker) => api.get(`/model-info?ticker=${ticker}`);
export const fetchTickers          = ()       => api.get("/tickers");
export const fetchExplanation = (ticker) => api.get(`/explain?ticker=${ticker}`);