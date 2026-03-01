# TRADESENPAI — API REFERENCE
### V4 · March 2026

---

**PRODUCTION**: `https://tradesenpaii-production.up.railway.app`  
**LOCAL DEV**: `http://localhost:8000`  
**API DOCS**: `/docs` (Swagger UI — interactive)

---

## 🔌 ENDPOINTS

### **01** `GET /health`
> API status, version, supported tickers  
> **Parameters**: None

### **02** `GET /tickers`
> List all supported tickers with company names  
> **Parameters**: None

### **03** `GET /predict?ticker=KO`
> Transformer model — UP/DOWN prediction + confidence  
> **Parameters**: `ticker` (`KO` | `JNJ` | `PG` | `WMT` | `AAPL` | `GOOGL`)  
> **Cache**: 30 minutes per ticker

### **04** `GET /price-history?ticker=KO`
> 200 days of OHLCV price data  
> **Parameters**: `ticker`

### **05** `GET /sentiment-history?ticker=KO`
> LM sentiment scores per SEC filing  
> **Parameters**: `ticker`

### **06** `GET /model-info?ticker=KO`
> CV accuracy, feature count, sequence length  
> **Parameters**: `ticker`

### **07** `GET /explain?ticker=KO`
> Historical analogies + LLM synthesis (~8s response)  
> **Parameters**: `ticker` | **Rate limit**: 10 req/min

### **08** `POST /hypothesis/stream`
> 6-agent research engine — streams SSE progress  
> **Body**:
```json
{"text": "Coca-Cola will reach $90 in 3 months"}
```
> **Rate limit**: 5 req/min

### **09** `POST /subscribe`
> Submit Telegram alert subscription request  
> **Body**:
```json
{"username": "john", "telegram_id": "123456789"}
```
> **Rate limit**: 3 req/min

### **10** `GET /subscribers` 🔐 *JWT ADMIN*
> List all subscribers with status and chat IDs  
> **Header**: `Authorization: Bearer <token>`

### **11** `POST /subscribers/{id}/approve` 🔐 *JWT ADMIN*
> Approve subscriber + send Telegram welcome message  
> **Body**:
```json
{"telegram_id": "123456789"}
```
> **Header**: `Authorization: Bearer <token>`

### **12** `POST /subscribers/{id}/reject` 🔐 *JWT ADMIN*
> Reject a pending subscriber request  
> **Header**: `Authorization: Bearer <token>`

---

## 📊 SUPPORTED TICKERS

| Ticker | Company | Sector |
|--------|---------|--------|
| `KO` | Coca-Cola | Consumer Staples |
| `JNJ` | Johnson & Johnson | Healthcare |
| `PG` | Procter & Gamble | Consumer Staples |
| `WMT` | Walmart | Retail |
| `AAPL` | Apple | Technology |
| `GOOGL` | Alphabet | Technology |

---

## 🔐 AUTHENTICATION

Admin endpoints require a **Supabase JWT** with `role=admin`

- **Header format**: `Authorization: Bearer <access_token>`
- **Token endpoint**: `POST {supabase_url}/auth/v1/token`
- **Algorithm**: `ES256` (Supabase default)

---

## ⚠️ ERROR CODES

| Code | Meaning |
|------|---------|
| `400` | Bad request — invalid ticker or missing body field |
| `401` | Unauthorized — missing or invalid JWT token |
| `403` | Forbidden — valid JWT but insufficient role |
| `404` | Not found — subscriber ID does not exist |
| `429` | Too many requests — rate limit exceeded |
| `500` | Internal server error — check Railway logs |

---

## 📝 NOTES

- ✅ All responses are `JSON`
- ✅ `/hypothesis/stream` uses **Server-Sent Events (SSE)**
- ✅ Model CV accuracy **~52%** across all tickers
- ✅ Predictions cached **30 min** — same ticker returns cached result
- ✅ Interactive docs available at `/docs` (Swagger UI)

> ⚠️ **EDUCATIONAL SIMULATION ONLY — NOT FINANCIAL ADVICE**