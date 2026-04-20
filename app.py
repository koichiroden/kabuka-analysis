"""
app.py  ── DB参照版
株価分析くん - Flask バックエンド（定時バッチ + DB 永続化対応）

変更点:
    /api/scan      → DB から最新スキャン結果を返す（高速）
    /api/stock/<code> → DB から最新個別データを返す
    /api/admin/run_scan → 手動でスキャンを即時実行（管理用）
    /api/admin/history  → スキャン実行履歴を返す

起動:
    python app.py  または  gunicorn app:app
"""

import os
import json
import time
import threading
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, render_template, send_from_directory
from flask_cors import CORS

import yfinance as yf
import pandas as pd
import numpy as np

from stocks import ALL_STOCKS
from analyzer import (
    calc_all_trends, score_stock,
    detect_local_minima, detect_local_maxima,
    calc_chart_curves, calc_limit_prices,
)
from notifier import send_notification
from database import (
    init_db, get_latest_run, get_latest_stocks,
    get_stock_latest, get_run_history,
)

app = Flask(__name__)
CORS(app)

# ---------------------------------------------------------------------------
# メモリキャッシュ（スキャン実行時に yfinance へアクセスする際の一時キャッシュ）
# ---------------------------------------------------------------------------
_cache: dict = {}
_CACHE_TTL_HOURS = 6


def is_cache_valid(ticker: str) -> bool:
    if ticker not in _cache:
        return False
    return datetime.now() - _cache[ticker]["fetched_at"] < timedelta(hours=_CACHE_TTL_HOURS)


# ---------------------------------------------------------------------------
# yfinance データ取得（変更なし）
# ---------------------------------------------------------------------------
def fetch_stock(stock_meta: dict) -> dict | None:
    ticker = stock_meta["ticker"]
    if is_cache_valid(ticker):
        return _cache[ticker]["data"]

    try:
        yf_ticker = yf.Ticker(ticker)
        hist = yf_ticker.history(period="1y", auto_adjust=True)
        if hist.empty or len(hist) < 5:
            return None

        closes = hist["Close"].dropna().tolist()
        dates  = [d.strftime("%Y-%m-%d") for d in hist.index]

        price      = closes[-1]
        price_prev = closes[-2] if len(closes) >= 2 else price

        info      = yf_ticker.info
        div_yield = (info.get("dividendYield") or 0) * 100
        per       = info.get("trailingPE")
        pbr       = info.get("priceToBook")

        trends      = calc_all_trends(closes)
        score_result= score_stock(closes, div_yield, trends)

        minima_idx = detect_local_minima(closes, order=5)
        maxima_idx = detect_local_maxima(closes, order=5)

        closes_120 = closes[-120:]
        curves     = calc_chart_curves(closes_120)
        limit_prices = calc_limit_prices(closes)

        offset_120 = max(0, len(closes) - 120)
        minima_120 = [i - offset_120 for i in minima_idx if i >= offset_120]
        maxima_120 = [i - offset_120 for i in maxima_idx if i >= offset_120]

        data = {
            **stock_meta,
            "price":          round(price, 1),
            "price_prev":     round(price_prev, 1),
            "change":         round(price - price_prev, 1),
            "change_pct":     round((price - price_prev) / price_prev * 100, 2) if price_prev else 0,
            "dividend_yield": round(div_yield, 2),
            "per":            round(per, 1) if per else None,
            "pbr":            round(pbr, 2) if pbr else None,
            "trends":         {k: round(v, 2) if v is not None else None for k, v in trends.items()},
            "score":          score_result["score"],
            "signals":        score_result["signals"],
            "buy_signal":     score_result["buy_signal"],
            "closes":         [round(c, 1) for c in closes_120],
            "dates":          dates[-120:],
            "minima_idx":     minima_120,
            "maxima_idx":     maxima_120,
            "curves":         curves,
            "limit_prices":   limit_prices,
        }

        _cache[ticker] = {"fetched_at": datetime.now(), "data": data}
        return data

    except Exception as e:
        print(f"[ERROR] {ticker}: {e}")
        return None


def fetch_stocks_parallel(stock_list: list[dict], max_workers: int = 8) -> list[dict]:
    results = [None] * len(stock_list)
    lock = threading.Lock()

    def worker(idx, meta):
        result = fetch_stock(meta)
        with lock:
            results[idx] = result

    threads = []
    for i, meta in enumerate(stock_list):
        t = threading.Thread(target=worker, args=(i, meta))
        threads.append(t)
        t.start()
        if (i + 1) % max_workers == 0:
            time.sleep(0.5)

    for t in threads:
        t.join()

    return [r for r in results if r is not None]


# ---------------------------------------------------------------------------
# API エンドポイント
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def status():
    run = get_latest_run("nikkei225")
    return jsonify({
        "status":       "ok",
        "last_scan":    run["executed_at"] if run else "未実行",
        "server_time":  datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "data_source":  "database",
    })


@app.route("/api/scan")
def scan():
    """
    【変更】DB から最新スキャン結果を返す。
    DB が空の場合はリアルタイム取得にフォールバック。
    """
    market    = request.args.get("market", "nikkei225")
    sector    = request.args.get("sector", "all")
    min_yield = float(request.args.get("min_yield", 0))
    limit     = request.args.get("limit", type=int)

    run, stocks_data = get_latest_stocks(
        market=market,
        sector=sector,
        min_yield=min_yield,
        limit=limit,
    )

    # DB が空なら従来どおりリアルタイム取得
    if not run:
        print("[API] DB にデータなし → リアルタイム取得にフォールバック")
        targets = ALL_STOCKS
        if market != "all":
            targets = [s for s in targets if s["market"] == market]
        stocks_data = fetch_stocks_parallel(targets)
        if sector != "all":
            stocks_data = [s for s in stocks_data if s.get("sector") == sector]
        stocks_data = [s for s in stocks_data if s.get("dividend_yield", 0) >= min_yield]
        stocks_data.sort(key=lambda x: x["score"], reverse=True)
        scan_date = datetime.now().strftime("%Y年%m月%d日 %H:%M") + "（リアルタイム）"
    else:
        dt = datetime.strptime(run["executed_at"], "%Y-%m-%d %H:%M:%S")
        scan_date = dt.strftime("%Y年%m月%d日 %H:%M") + " 時点のデータ"

    n           = len(stocks_data)
    avg_yield   = round(sum(s.get("dividend_yield", 0) for s in stocks_data) / n, 2) if n else 0
    buy_count   = sum(1 for s in stocks_data if s.get("buy_signal") == "今すぐ買い")
    watch_count = sum(1 for s in stocks_data if s.get("buy_signal") == "要注目")
    high_yield  = sum(1 for s in stocks_data if s.get("dividend_yield", 0) >= 3)

    return jsonify({
        "scan_date": scan_date,
        "total":     n,
        "summary": {
            "avg_yield":   avg_yield,
            "buy_count":   buy_count,
            "watch_count": watch_count,
            "high_yield":  high_yield,
        },
        "stocks": stocks_data,
    })


@app.route("/api/stock/<code>")
def stock_detail(code):
    """【変更】DB から最新個別データを返す。なければリアルタイム取得。"""
    # DB から検索
    data = get_stock_latest(code)

    if not data:
        # DB になければリアルタイム
        meta = next((s for s in ALL_STOCKS if s["code"] == code), None)
        if not meta:
            return jsonify({"error": "銘柄が見つかりません"}), 404
        data = fetch_stock(meta)
        if not data:
            return jsonify({"error": "データ取得に失敗しました"}), 500

    return jsonify(data)


# ---------------------------------------------------------------------------
# 管理用 API
# ---------------------------------------------------------------------------
@app.route("/api/admin/run_scan", methods=["POST"])
def admin_run_scan():
    """手動でスキャンを即時実行する（管理用）"""
    # 簡易認証
    body   = request.get_json() or {}
    secret = os.environ.get("ADMIN_SECRET", "")
    if secret and body.get("secret") != secret:
        return jsonify({"error": "認証エラー"}), 403

    market = body.get("market", "all")

    # バックグラウンドで実行
    from scheduler import run_daily_scan
    t = threading.Thread(target=run_daily_scan, kwargs={"market": market})
    t.daemon = True
    t.start()

    return jsonify({
        "message": f"スキャンを開始しました (market={market})",
        "started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })


@app.route("/api/admin/history")
def admin_history():
    """スキャン実行履歴を返す"""
    limit = int(request.args.get("limit", 30))
    return jsonify(get_run_history(limit))


# ---------------------------------------------------------------------------
# 既存エンドポイント（変更なし）
# ---------------------------------------------------------------------------
@app.route("/api/notify", methods=["POST"])
def notify():
    body = request.get_json()
    if not body:
        return jsonify({"error": "リクエストボディが不正です"}), 400

    email     = body.get("email", "")
    min_score = int(body.get("min_score", 60))
    market    = body.get("market", "nikkei225")

    if "@" not in email:
        return jsonify({"error": "メールアドレスが不正です"}), 400

    _, stocks_data = get_latest_stocks(market=market)
    buy_stocks = [s for s in stocks_data if s.get("score", 0) >= min_score]
    buy_stocks.sort(key=lambda x: x["score"], reverse=True)

    result = send_notification(email, buy_stocks)
    return jsonify(result)


@app.route("/api/cache/clear", methods=["POST"])
def clear_cache():
    _cache.clear()
    return jsonify({"message": "メモリキャッシュをクリアしました"})


@app.route("/favicon.ico")
def favicon():
    return "", 204


@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory(os.path.join(os.path.dirname(__file__), "static"), filename)


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"]  = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


@app.route("/api/<path:dummy>", methods=["OPTIONS"])
def options_handler(dummy):
    return "", 204


# ---------------------------------------------------------------------------
# 起動
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # スケジューラー起動（gunicorn 経由の場合は gunicorn_config.py で起動）
    from scheduler import start_scheduler
    start_scheduler()

    print("=" * 50)
    print("  株価分析くん（DB版）起動中...")
    print("  ブラウザで → http://localhost:5000")
    print("=" * 50)
    app.run(debug=False, host="0.0.0.0", port=5000, threaded=True)
