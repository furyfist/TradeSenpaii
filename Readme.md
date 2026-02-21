# TradeSenpai

AI-Powered Stock Advisor for Coca-Cola (KO)

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.95%2B-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18%2B-blue.svg)](https://reactjs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

TradeSenpai is an AI-powered stock research tool focused on Coca-Cola (KO) that combines historical stock price patterns and sentiment analysis from SEC regulatory filings to generate a next-day directional prediction (UP or DOWN). It addresses information asymmetry in retail investing by automating the analysis of SEC filings (8-K, 10-Q, 10-K), extracting financial sentiment using the Loughran-McDonald dictionary, and integrating it with technical indicators via a Transformer machine learning model.

The system includes:
- A Python data pipeline for fetching and processing data.
- A trained Transformer model for predictions.
- A FastAPI backend for serving predictions and data.
- A React frontend dashboard for visualization.

This is not a "predict stock prices" tool—it's designed to surface signals (e.g., sentiment history, technical indicators) that institutional analysts use, automated for retail investors. The model achieves ~52.72% cross-validation accuracy on next-day direction, which is realistic for financial markets.

## Features

- **Next-Day Directional Prediction**: Binary classification (UP/DOWN) with confidence score.
- **Signal Breakdown**: Displays key drivers like RSI, moving averages, volatility, and sentiment scores.
- **Real-Time Data Integration**: Fetches live KO prices from Yahoo Finance and combines with historical SEC sentiment.
- **Dashboard Visualizations**:
  - 90-day price chart.
  - Sentiment history gauge.
  - Prediction card with metadata.
- **Feature Set**: 56 engineered features including price indicators (e.g., MA7/20/50/200, RSI-14, Bollinger Bands), calendar features, Loughran-McDonald sentiment metrics (positive, negative, uncertainty, etc.), and interactions.
- **Data Sources**:
  - Historical OHLCV from Yahoo Finance (1963–present).
  - SEC EDGAR filings (1994–present) for sentiment.

## Prerequisites

- Python 3.8+
- PostgreSQL database
- Node.js 16+ and npm for the frontend
- Libraries: Install via `requirements.txt` (assumed to include yfinance, sec-edgar-downloader, pandas, numpy, torch, fastapi, uvicorn, recharts, etc.)
- Kaggle account (optional, for initial model training on GPU)

## Installation

1. **Clone the Repository**:
   ```
   git clone https://github.com/yourusername/TradeSenpai.git
   cd TradeSenpai
   ```

2. **Set Up Python Environment**:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Set Up PostgreSQL**:
   - Create a database (e.g., `tradesenpai_db`).
   - Update connection strings in scripts (e.g., `data_loader.py`) with your credentials (hardcoded for now; consider env vars).

4. **Frontend Setup**:
   ```
   cd frontend
   npm install
   ```

5. **Download and Process Data** (Initial Setup):
   Run the data pipeline scripts in sequence:
   ```
   python scripts/fetch_stock_data.py
   python scripts/data_loader.py
   python scripts/fetch_sec_filings.py
   python scripts/preprocess_filings.py
   python scripts/lm_sentiment.py
   python scripts/merge_datasets.py
   ```
   This generates `merged_dataset.csv` for training.

6. **Train the Model** (Optional; pre-trained model available as `transformer_ko.pt`):
   - Run the training notebook on Kaggle (with T4 GPU).
   - Uses TimeSeriesSplit for cross-validation.
   - Saves model to `models/transformer_ko.pt`.

## Usage

1. **Run the Backend (FastAPI)**:
   ```
   cd backend
   uvicorn main:app --reload --port 8000
   ```
   Endpoints:
   - `/health`: Liveness check.
   - `/predict`: Get latest prediction, confidence, and signal breakdown.
   - `/price-history`: Last 90 days OHLCV.
   - `/sentiment-history`: Last 50 sentiment points.
   - `/model-info`: Model metadata.

2. **Run the Frontend (React)**:
   ```
   cd frontend
   npm run dev
   ```
   Open `http://localhost:5173` (Vite default). The dashboard fetches data from the backend and displays predictions, charts, and signals.

3. **Generating a Prediction**:
   - The backend fetches real-time data on `/predict`.
   - Example output: "DOWN with 70.3% confidence" (as of Feb 21, 2026 sample).

## System Architecture

### Data Pipeline
Six sequential Python scripts:
- `fetch_stock_data.py`: Downloads OHLCV from yfinance.
- `data_loader.py`: Loads to PostgreSQL.
- `fetch_sec_filings.py`: Downloads SEC filings via sec-edgar-downloader.
- `preprocess_filings.py`: Extracts relevant text (MD&A, item bodies).
- `lm_sentiment.py`: Computes sentiment using Loughran-McDonald.
- `merge_datasets.py`: Joins datasets, engineers features.

### Model
- Transformer (d_model=128, 4 heads, 3 layers, 60-day lookback).
- Trained on 8,073 samples (1994–Jan 2026).
- Binary classification; 52.72% CV accuracy.

### Backend
- FastAPI on port 8000 with caching.

### Frontend
- React/Vite with Recharts for charts.
- Two-column dashboard: Prediction + signals (left), charts (right).

## Known Limitations

- Single stock (KO only); no generalization.
- 52.72% accuracy—marginally above 51.17% baseline due to market noise.
- Sentiment forward-filled between filings (assumes persistence).
- No earnings calendar awareness.
- Excludes macro features (e.g., VIX, S&P500).
- Relies on yfinance (rate limits, no SLA).
- No prediction logging for live tracking.
- Local deployment only; single-user.

## Technical Debt

- Inline CSS in React (no framework).
- No tests (unit/integration).
- Hardcoded paths and credentials.
- Brittle regex in preprocessing.
- Model reloaded on every restart.
- Partial LM dictionary (full has 86k+ words).
- No env variable management.

## Lessons Learned

- Domain-specific tools (e.g., Loughran-McDonald) beat general models for specific data.
- Inspect data before modeling to avoid mismatches.
- Ensure training-inference consistency to prevent skew.
- Scope ruthlessly for V1 to ship a complete product.
- 52% accuracy is honest and shippable—focus on signal value.
- Positioning: Frame as "automated analyst" not "price predictor."

## Contributing

Contributions welcome! Fork the repo, create a branch, and submit a PR. Focus on fixes for technical debt or limitations.

## License

MIT License. See [LICENSE](LICENSE) for details.

Version 1.0 - February 2026