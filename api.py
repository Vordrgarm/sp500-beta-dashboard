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
    """
    OLS regression: β = Cov(Ri, Rm) / Var(Rm)
    Uses sample variance (ddof=1) and monthly returns to match Yahoo Finance methodology.
    """
    if len(returns_stock) < 12:
        return None
    cov = np.cov(returns_stock, returns_market)[0][1]
    var = np.var(returns_market, ddof=1)
    return round(cov / var, 4) if var != 0 else None

def get_available_history(ticker):
    """Check how many years of data are available for a ticker."""
    try:
        hist = yf.Ticker(ticker).history(period="max")
        if hist.empty:
            return 0
        years = (hist.index[-1] - hist.index[0]).days / 365.25
        return round(years, 1)
    except:
        return 0

@app.route('/')
def serve_frontend():
    return send_from_directory('frontend', 'index.html')

@app.route("/beta")
def get_bulk_beta():
    """Current beta for all 50 stocks using 5y monthly returns vs ^GSPC."""
    tickers = SP500 + ["^GSPC"]
    raw     = yf.download(tickers, period="5y", auto_adjust=True, progress=False)["Close"]
    monthly = raw.resample("ME").last()
    returns = monthly.pct_change().dropna()
    market  = returns["^GSPC"]

    results = []
    for t in SP500:
        if t not in returns.columns:
            continue
        b_calc = calc_beta(returns[t].values, market.values)

        try:
            info   = yf.Ticker(t).info
            b_yf   = info.get("beta")
            name   = info.get("shortName", t)
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
            "method":     "Monthly returns · 5y · ^GSPC · sample variance (ddof=1)",
            "verify_url": f"https://finance.yahoo.com/quote/{t}/key-statistics/",
            "timestamp":  datetime.now().isoformat()
        })

    return jsonify(sorted(results, key=lambda x: x["ticker"]))

@app.route("/beta/single")
def get_single_beta():
    """
    Deep-dive for one stock:
    - Current beta (5y monthly vs ^GSPC)
    - Rolling 5y beta snapshots at 1-year intervals (as far back as data allows)
    - Monthly returns for the chart
    - Full stock info
    """
    ticker = request.args.get("ticker", "AAPL").upper()

    # Download maximum available history for rolling analysis
    raw_max  = yf.download([ticker, "^GSPC"], period="max", auto_adjust=True, progress=False)["Close"]
    monthly  = raw_max.resample("ME").last()
    returns  = monthly.pct_change().dropna()

    # Check data availability
    years_available = round((returns.index[-1] - returns.index[0]).days / 365.25, 1)

    # Current beta — standard 5y window
    last_60  = returns.tail(60)
    b_calc   = calc_beta(last_60[ticker].values, last_60["^GSPC"].values) if ticker in last_60.columns else None

    # Rolling beta snapshots — 5-year window ending at each year-end we have data for
    # Step back in 12-month increments from today, as far as data allows
    rolling_betas = []
    end_idx = len(returns)
    window  = 60  # 60 monthly observations = 5 years

    while end_idx >= window:
        window_data = returns.iloc[end_idx - window : end_idx]
        if ticker not in window_data.columns:
            break
        snap_beta = calc_beta(window_data[ticker].values, window_data["^GSPC"].values)
        snap_date = str(returns.index[end_idx - 1].date())
        if snap_beta is not None:
            rolling_betas.append({"date": snap_date, "beta": snap_beta})
        end_idx -= 12  # step back 1 year

    rolling_betas.reverse()  # chronological order

    # Monthly returns for chart (last 5 years)
    monthly_hist = returns[ticker].tail(60) if ticker in returns.columns else pd.Series()
    monthly_returns = [
        {"date": str(d.date()), "return": round(v * 100, 2)}
        for d, v in monthly_hist.items()
    ]

    # Stock info
    info = yf.Ticker(ticker).info

    return jsonify({
        "ticker":          ticker,
        "name":            info.get("shortName"),
        "sector":          info.get("sector"),
        "beta_calc":       b_calc,
        "beta_yahoo":      round(info.get("beta"), 4) if info.get("beta") else None,
        "price":           info.get("currentPrice"),
        "marketCap":       info.get("marketCap"),
        "high52":          info.get("fiftyTwoWeekHigh"),
        "low52":           info.get("fiftyTwoWeekLow"),
        "years_available": years_available,
        "rolling_betas":   rolling_betas,
        "monthly_returns": monthly_returns,
        "method":          "Monthly returns · 5y rolling · ^GSPC · sample variance (ddof=1)",
        "verify_url":      f"https://finance.yahoo.com/quote/{ticker}/key-statistics/",
    })

@app.route("/beta/history")
def get_beta_history():
    """
    Rolling 5y beta history for up to 5 tickers at once — used for comparison chart.
    """
    raw_tickers = request.args.get("tickers", "AAPL").split(",")
    tickers     = [t.strip().upper() for t in raw_tickers[:5]]
    symbols     = tickers + ["^GSPC"]

    raw_max  = yf.download(symbols, period="max", auto_adjust=True, progress=False)["Close"]
    monthly  = raw_max.resample("ME").last()
    returns  = monthly.pct_change().dropna()

    result = {}
    window = 60

    for t in tickers:
        if t not in returns.columns:
            continue
        betas   = []
        end_idx = len(returns)
        while end_idx >= window:
            wd        = returns.iloc[end_idx - window : end_idx]
            snap_beta = calc_beta(wd[t].values, wd["^GSPC"].values)
            snap_date = str(returns.index[end_idx - 1].date())
            if snap_beta is not None:
                betas.append({"date": snap_date, "beta": snap_beta})
            end_idx -= 12
        betas.reverse()
        result[t] = betas

    return jsonify(result)

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