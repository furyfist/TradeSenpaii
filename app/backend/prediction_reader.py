import os, json
import psycopg2

def get_prediction(ticker: str) -> dict:
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur  = conn.cursor()
    cur.execute("SELECT * FROM seeded_predictions WHERE ticker = %s", (ticker,))
    row  = cur.fetchone()
    cols = [d[0] for d in cur.description]
    cur.close()
    conn.close()
    if not row:
        raise ValueError(f"No seeded prediction found for {ticker}")
    data = dict(zip(cols, row))
    if isinstance(data["top_signals"], str):
        data["top_signals"] = json.loads(data["top_signals"])
    return data
