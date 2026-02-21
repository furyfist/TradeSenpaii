import torch
import torch.nn as nn
import numpy as np
import pandas as pd
from pathlib import Path

MODEL_PATH = Path("model/transformer_ko.pt")


# ── Replicate exact architecture from training ──
class PositionalEncoding(nn.Module):
    def __init__(self, d_model, max_len=200, dropout=0.1):
        super().__init__()
        self.dropout = nn.Dropout(dropout)
        pe           = torch.zeros(max_len, d_model)
        position     = torch.arange(0, max_len).unsqueeze(1).float()
        div_term     = torch.exp(
            torch.arange(0, d_model, 2).float() * (-np.log(10000.0) / d_model)
        )
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer("pe", pe.unsqueeze(0))

    def forward(self, x):
        return self.dropout(x + self.pe[:, :x.size(1)])


class StockTransformer(nn.Module):
    def __init__(self, input_size, d_model=128, nhead=4,
                 num_layers=3, num_classes=2, dropout=0.3):
        super().__init__()
        self.input_proj  = nn.Linear(input_size, d_model)
        self.pos_enc     = PositionalEncoding(d_model, dropout=dropout)
        encoder_layer    = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=nhead,
            dim_feedforward=d_model * 4,
            dropout=dropout, batch_first=True, norm_first=True
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.norm        = nn.LayerNorm(d_model)
        self.classifier  = nn.Sequential(
            nn.Linear(d_model, 64), nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(64, num_classes)
        )

    def forward(self, x):
        x = self.input_proj(x)
        x = self.pos_enc(x)
        x = self.transformer(x)
        x = self.norm(x)
        x = x[:, -1, :]
        return self.classifier(x)


class Predictor:
    def __init__(self):
        print("[INFO] Loading Transformer model...")
        checkpoint = torch.load(MODEL_PATH, map_location="cpu", weights_only=False)

        self.feature_cols  = checkpoint["feature_cols"]
        self.sequence_len  = checkpoint["sequence_len"]
        self.scaler_mean   = np.array(checkpoint["scaler_mean"])
        self.scaler_scale  = np.array(checkpoint["scaler_scale"])
        self.cv_accuracy   = checkpoint["cv_accuracy"]
        self.trained_on    = checkpoint["trained_on"]
        self.model_config  = checkpoint["model_config"]

        cfg         = self.model_config
        self.model  = StockTransformer(
            input_size=cfg["input_size"],
            d_model=cfg["d_model"],
            nhead=cfg["nhead"],
            num_layers=cfg["num_layers"],
            num_classes=cfg["num_classes"],
            dropout=cfg["dropout"]
        )
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.model.eval()
        print(f"[INFO] Model loaded — CV accuracy: {self.cv_accuracy:.4f}")

    def scale(self, X: np.ndarray) -> np.ndarray:
        return (X - self.scaler_mean) / self.scaler_scale

    def predict(self, feature_df: pd.DataFrame) -> dict:
        # Select and order features exactly as training
        available = [c for c in self.feature_cols if c in feature_df.columns]
        X = feature_df[available].values

        # Scale
        X_scaled = self.scale(X)

        # Need at least sequence_len rows
        if len(X_scaled) < self.sequence_len:
            raise ValueError(
                f"Need at least {self.sequence_len} rows, got {len(X_scaled)}"
            )

        # Take last sequence_len rows
        sequence = X_scaled[-self.sequence_len:]
        tensor   = torch.FloatTensor(sequence).unsqueeze(0)  # (1, seq, features)

        with torch.no_grad():
            logits = self.model(tensor)
            probs  = torch.softmax(logits, dim=1).squeeze().numpy()

        pred_class  = int(probs.argmax())
        confidence  = float(probs.max())
        prediction  = "UP" if pred_class == 1 else "DOWN"

        # Top signals — last row feature values
        last_row     = feature_df[available].iloc[-1]
        top_signals  = self._get_top_signals(last_row, prediction)

        return {
            "prediction":  prediction,
            "confidence":  round(confidence, 4),
            "prob_up":     round(float(probs[1]), 4),
            "prob_down":   round(float(probs[0]), 4),
            "top_signals": top_signals,
        }

    def _get_top_signals(self, row: pd.Series, prediction: str) -> list[dict]:
        """
        Returns the 6 most interpretable signals driving the prediction.
        Hardcoded to the most important features from XGBoost importance.
        """
        signals = []

        signal_map = {
            "rsi_14":              ("RSI",                 lambda v: "Oversold"  if v < 30 else ("Overbought" if v > 70 else "Neutral")),
            "lm_sentiment_score":  ("SEC Sentiment",       lambda v: "Positive"  if v > 0.5 else ("Negative" if v < -0.5 else "Neutral")),
            "lm_uncertain_pct":    ("Uncertainty",         lambda v: "High"      if v > 1.5 else "Normal"),
            "lm_neg_pct":          ("Negative Language",   lambda v: "Elevated"  if v > 1.5 else "Normal"),
            "distance_from_ma20":  ("Price vs MA20",       lambda v: "Above"     if v > 0 else "Below"),
            "ma20_above_ma50":     ("Trend",               lambda v: "Bullish"   if v == 1 else "Bearish"),
            "volatility_20":       ("Volatility",          lambda v: "High"      if v > 1.5 else "Low"),
            "volume_surge":        ("Volume",              lambda v: "Surge"     if v == 1 else "Normal"),
            "lm_litigation_spike": ("Litigation Risk",     lambda v: "Spike"     if v == 1 else "Normal"),
            "momentum_5d":         ("5D Momentum",         lambda v: "Positive"  if v > 0 else "Negative"),
        }

        for col, (label, interpreter) in signal_map.items():
            if col in row.index:
                val = float(row[col])
                signals.append({
                    "name":  label,
                    "value": round(val, 4),
                    "state": interpreter(val),
                })

        return signals[:6]