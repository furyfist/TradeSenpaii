import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:8000",
  timeout: 30000,
});

export const fetchPrediction     = () => api.get("/predict");
export const fetchPriceHistory   = () => api.get("/price-history");
export const fetchSentimentHistory = () => api.get("/sentiment-history");
export const fetchModelInfo      = () => api.get("/model-info");