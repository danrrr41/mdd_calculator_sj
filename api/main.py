from fastapi import FastAPI
from fastapi.responses import JSONResponse, FileResponse
import yfinance as yf
import pandas as pd
import numpy as np
import os

app = FastAPI()

SITE_PASSWORD = "0603"

# 프로젝트 루트 경로 계산
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 홈페이지 접속 로직 (app.mount 대신 사용)
@app.get("/")
async def read_index():
    return FileResponse(os.path.join(BASE_DIR, 'public', 'index.html'))

@app.get("/api/calculate")
async def calculate(
        code: str = "QQQ",
        start: str = "2004-01-01",
        end: str = "2026-01-30",
        threshold: float = 80.0,
        pw: str = ""
):
    if pw != SITE_PASSWORD:
        return JSONResponse(status_code=401, content={"message": "비밀번호가 올바르지 않습니다."})

    try:
        df = yf.download(code, start=start, end=end, progress=False)
        if df.empty:
            return JSONResponse(status_code=400, content={"message": "데이터 없음"})

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        price_col = 'Adj Close' if 'Adj Close' in df.columns else 'Close'
        df = df[[price_col]].copy()
        df.columns = ['Price']

        df['Peak'] = df['Price'].cummax()
        df['Drawdown'] = (df['Price'] - df['Peak']) / df['Peak'] * 100

        max_mdd_val = df['Drawdown'].min()
        max_mdd_date = df['Drawdown'].idxmin()
        current_peak = df['Peak'].iloc[-1]

        threshold_val_pct = np.percentile(df['Drawdown'], 100 - threshold)
        price_at_threshold = current_peak * (1 + threshold_val_pct / 100)

        chart_data = [{"x": int(ts.timestamp() * 1000), "y": round(val, 2)}
                      for ts, val in df['Drawdown'].items()]

        total_days = len(df)
        table_rows = []
        for ts in range(0, -105, -5):
            r_rate = len(df[df['Drawdown'] >= ts]) / total_days * 100
            w_days = len(df[df['Drawdown'] == 0]) if ts == 0 else len(
                df[(df['Drawdown'] >= ts) & (df['Drawdown'] < ts + 5)])
            weight = w_days / total_days * 100
            table_rows.append({"mdd": f"{ts}%", "recovery": round(r_rate, 1), "weight": round(weight, 1)})

        return {
            "chart_data": chart_data,
            "table_data": table_rows,
            "threshold_line": round(threshold_val_pct, 2),
            "stats": {
                "max_mdd": round(max_mdd_val, 2), "max_mdd_date": max_mdd_date.strftime('%Y-%m-%d'),
                "last_price": round(df['Price'].iloc[-1], 2), "last_val": round(df['Drawdown'].iloc[-1], 2),
                "peak_price": round(current_peak, 2), "price_at_threshold": round(price_at_threshold, 2),
                "last_date": df.index[-1].strftime('%Y-%m-%d')
            }
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})