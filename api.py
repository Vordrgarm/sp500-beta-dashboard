from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import yfinance as yf
import numpy as np
import pandas as pd
from datetime import datetime
import os

app = Flask(__name__, static_folder='frontend', static_url_path='')
CORS(app)

SP500 = [
    "AAPL","MSFT","NVDA","AMZN","META","GOOGL","TSLA","BRK-B","JPM","LLY",
    "V","UNH","XOM","MA","AVGO","PG","JNJ","HD","COST","MRK",
    "ABBV","CVX","CRM","BAC","NFLX","PEP","KO","TMO","WMT","ACN",
    "MCD","ABT","CSCO","LIN","TXN","DHR","NEE","PM","ADBE","AMD",
    "DIS","INTU","WFC","CAT","GE","RTX","AMGN","ISRG","SPGI","HON"
]

def calc_beta(returns_stock, returns_market):
    cov = np.cov(returns_stock, returns_market)[0][1]
    var = np.var(returns_market)
    return round(cov / var, 4) if var != 0 else None

@app.route('/')
def serve_frontend():
    return send_from_directory('frontend', 'index.html')

@app.route("/beta")
def get_bulk_beta():
    period = request.args.get("period", "1y")
    tickers = SP500 + ["SPY"]
    raw = yf.download(tickers, period=period, auto_adjust=True, progress=False)["Close"]
    returns = raw.pct_change().dropna()
    market = returns["SPY"]

    results = []
    for t in SP500:
        if t not in returns.columns:
            continue
        stock = returns[t]
        b_calc = calc_beta(stock.values, market.values)
        try:
            info = yf.Ticker(t).info
            b_yf = info.get("beta")
            name = info.get("shortName", t)
            sector = info.get("sector", "Unknown")
        except:
            b_yf, name, sector = None, t, "Unknown"

        results.append({
            "ticker":     t,
            "name":       name,
            "sector":     sector,
            "beta_calc":  b_calc,
            "beta_yahoo": round(b_yf, 4) if b_yf else None,
            "delta":      round(abs(b_calc - b_yf), 4) if (b_calc and b_yf) else None,
            "period":     period,
            "verify_url": f"https://finance.yahoo.com/quote/{t}/key-statistics/",
            "timestamp":  datetime.now().isoformat()
        })

    return jsonify(sorted(results, key=lambda x: x["ticker"]))

@app.route("/beta/single")
def get_single_beta():
    ticker = request.args.get("ticker", "AAPL").upper()
    period = request.args.get("period", "1y")
    raw = yf.download([ticker, "SPY"], period=period, auto_adjust=True, progress=False)["Close"]
    returns = raw.pct_change().dropna()
    b_calc = calc_beta(returns[ticker].values, returns["SPY"].values)
    info = yf.Ticker(ticker).info
    hist = yf.Ticker(ticker).history(period=period)
    monthly = hist["Close"].resample("ME").last().pct_change().dropna()

    return jsonify({
        "ticker":     ticker,
        "name":       info.get("shortName"),
        "sector":     info.get("sector"),
        "beta_calc":  b_calc,
        "beta_yahoo": round(info.get("beta"), 4) if info.get("beta") else None,
        "price":      info.get("currentPrice"),
        "marketCap":  info.get("marketCap"),
        "high52":     info.get("fiftyTwoWeekHigh"),
        "low52":      info.get("fiftyTwoWeekLow"),
        "monthly_returns": [
            {"date": str(d.date()), "return": round(v * 100, 2)}
            for d, v in monthly.items()
        ],
        "verify_url": f"https://finance.yahoo.com/quote/{ticker}/key-statistics/",
    })

@app.route("/quote")
def get_quote():
    tickers = request.args.get("tickers", "AAPL").split(",")
    results = []
    for t in tickers:
        info = yf.Ticker(t.strip().upper()).info
        results.append({
            "ticker":        t.upper(),
            "name":          info.get("shortName"),
            "price":         info.get("currentPrice") or info.get("regularMarketPrice"),
            "change":        info.get("regularMarketChange"),
            "changePercent": info.get("regularMarketChangePercent"),
        })
    return jsonify(results)

@app.route("/health")
def health():
    return jsonify({"status": "ok", "time": datetime.now().isoformat()})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)