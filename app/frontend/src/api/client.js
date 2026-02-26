import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  timeout: 30000,
});

export const fetchPrediction       = (ticker) => api.get(`/predict?ticker=${ticker}`);
export const fetchPriceHistory     = (ticker) => api.get(`/price-history?ticker=${ticker}`);
export const fetchSentimentHistory = (ticker) => api.get(`/sentiment-history?ticker=${ticker}`);
export const fetchModelInfo        = (ticker) => api.get(`/model-info?ticker=${ticker}`);
export const fetchTickers          = ()       => api.get("/tickers");
export const fetchExplanation = (ticker) => api.get(`/explain?ticker=${ticker}`);