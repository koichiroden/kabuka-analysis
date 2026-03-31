"""
app.py
株価分析くん - Flask バックエンド
yfinance で前日終値・配当利回り・株価履歴を取得し、
analyzer.py でスコアリングして JSON API として提供する。

起動方法:
    python app.py

API エンドポイント:
    GET  /api/scan?market=nikkei225&sector=all&min_yield=0
         → 銘柄一覧 + スコア
    GET  /api/stock/<code>
         → 個別銘柄の詳細 (株価履歴付き)
    POST /api/notify
         → メール通知  body: {"email": "...", "min_score": 60}
    GET  /api/status
         → サーバー稼働確認
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

app = Flask(__name__)
CORS(app)

# ---------------------------------------------------------------------------
# キャッシュ (1日1回の取得で十分なため)
# ---------------------------------------------------------------------------
_cache: dict = {}          # {ticker: {"fetched_at": datetime, "data": {...}}}
_CACHE_TTL_HOURS = 6       # 6時間キャッシュ


def is_cache_valid(ticker: str) -> bool:
    if ticker not in _cache:
        return False
    elapsed = datetime.now() - _cache[ticker]["fetched_at"]
    return elapsed < timedelta(hours=_CACHE_TTL_HOURS)


# ---------------------------------------------------------------------------
# yfinance データ取得
# ---------------------------------------------------------------------------
def fetch_stock(stock_meta: dict) -> dict | None:
    ticker = stock_meta["ticker"]

    if is_cache_valid(ticker):
        return _cache[ticker]["data"]

    try:
        yf_ticker = yf.Ticker(ticker)

        # 株価履歴 (1年分)
        hist = yf_ticker.history(period="1y", auto_adjust=True)
        if hist.empty or len(hist) < 5:
            return None

        closes = hist["Close"].dropna().tolist()
        dates  = [d.strftime("%Y-%m-%d") for d in hist.index]

        # 前日終値 / 前々日終値
        price      = closes[-1]
        price_prev = closes[-2] if len(closes) >= 2 else price

        # 配当利回り
        info = yf_ticker.info
        div_yield = (info.get("dividendYield") or 0) * 100  # 0.03 → 3.0

        # PER / PBR
        per = info.get("trailingPE")
        pbr = info.get("priceToBook")

        # トレンド計算
        trends = calc_all_trends(closes)

        # スコアリング
        score_result = score_stock(closes, div_yield, trends)

        # 極小値・極大値インデックス（全期間）
        minima_idx = detect_local_minima(closes, order=5)
        maxima_idx = detect_local_maxima(closes, order=5)

        # 平滑化曲線・微分曲線（直近120日分）
        closes_120 = closes[-120:]
        curves     = calc_chart_curves(closes_120)

        # 指値推奨価格
        limit_prices = calc_limit_prices(closes)

        # 直近120日内のインデックスに絞り込む（チャート表示用）
        offset_120 = max(0, len(closes) - 120)
        minima_120 = [i - offset_120 for i in minima_idx if i >= offset_120]
        maxima_120 = [i - offset_120 for i in maxima_idx if i >= offset_120]

        data = {
            **stock_meta,
            "price":          round(price, 1),
            "price_prev":     round(price_prev, 1),
            "change":         round(price - price_prev, 1),
            "change_pct":     round((price - price_prev) / price_prev * 100, 2)
                              if price_prev else 0,
            "dividend_yield": round(div_yield, 2),
            "per":            round(per, 1) if per else None,
            "pbr":            round(pbr, 2) if pbr else None,
            "trends":         {k: round(v, 2) if v is not None else None
                               for k, v in trends.items()},
            "score":          score_result["score"],
            "signals":        score_result["signals"],
            "buy_signal":     score_result["buy_signal"],
            # チャート用（直近120日）
            "closes":         [round(c, 1) for c in closes_120],
            "dates":          dates[-120:],
            "minima_idx":     minima_120,
            "maxima_idx":     maxima_120,
            # 平滑化・微分曲線
            "curves":         curves,
            # 指値推奨
            "limit_prices":   limit_prices,
        }

        _cache[ticker] = {"fetched_at": datetime.now(), "data": data}
        return data

    except Exception as e:
        print(f"[ERROR] {ticker}: {e}")
        return None


def fetch_stocks_parallel(stock_list: list[dict], max_workers: int = 8) -> list[dict]:
    """マルチスレッドで複数銘柄を並列取得"""
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
        # Yahoo Finance レート制限対策: 少し間隔を空ける
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
    return jsonify({
        "status": "ok",
        "cached_tickers": list(_cache.keys()),
        "server_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })


@app.route("/api/scan")
def scan():
    """
    クエリパラメータ:
        market    : nikkei225 | growth | all  (デフォルト: nikkei225)
        sector    : all | 製造業 | 通信 | ...
        min_yield : float (デフォルト: 0)
        limit     : int   (デフォルト: 全件)
    """
    market    = request.args.get("market", "nikkei225")
    sector    = request.args.get("sector", "all")
    min_yield = float(request.args.get("min_yield", 0))
    limit     = request.args.get("limit", type=int)

    # 対象銘柄フィルタリング
    targets = ALL_STOCKS
    if market != "all":
        targets = [s for s in targets if s["market"] == market]

    stocks_data = fetch_stocks_parallel(targets)

    # 後フィルタ
    if sector != "all":
        stocks_data = [s for s in stocks_data if s["sector"] == sector]
    stocks_data = [s for s in stocks_data if s["dividend_yield"] >= min_yield]

    # スコア降順ソート
    stocks_data.sort(key=lambda x: x["score"], reverse=True)

    if limit:
        stocks_data = stocks_data[:limit]

    # サマリー統計
    n = len(stocks_data)
    avg_yield    = round(sum(s["dividend_yield"] for s in stocks_data) / n, 2) if n else 0
    buy_count    = sum(1 for s in stocks_data if s["buy_signal"] == "今すぐ買い")
    watch_count  = sum(1 for s in stocks_data if s["buy_signal"] == "要注目")
    high_yield   = sum(1 for s in stocks_data if s["dividend_yield"] >= 3)

    return jsonify({
        "scan_date": datetime.now().strftime("%Y年%m月%d日 %H:%M"),
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
    """個別銘柄の詳細情報 (フル株価履歴付き)"""
    meta = next((s for s in ALL_STOCKS if s["code"] == code), None)
    if not meta:
        return jsonify({"error": "銘柄が見つかりません"}), 404

    # キャッシュを無効化してフレッシュ取得するオプション
    refresh = request.args.get("refresh", "false").lower() == "true"
    if refresh and meta["ticker"] in _cache:
        del _cache[meta["ticker"]]

    data = fetch_stock(meta)
    if not data:
        return jsonify({"error": "データ取得に失敗しました"}), 500

    return jsonify(data)


@app.route("/api/notify", methods=["POST"])
def notify():
    """メール通知エンドポイント"""
    body = request.get_json()
    if not body:
        return jsonify({"error": "リクエストボディが不正です"}), 400

    email     = body.get("email", "")
    min_score = int(body.get("min_score", 60))
    market    = body.get("market", "nikkei225")

    if "@" not in email:
        return jsonify({"error": "メールアドレスが不正です"}), 400

    # キャッシュ済みデータから買い時銘柄を抽出
    buy_stocks = [
        v["data"] for v in _cache.values()
        if v["data"].get("score", 0) >= min_score
        and (market == "all" or v["data"].get("market") == market)
    ]
    buy_stocks.sort(key=lambda x: x["score"], reverse=True)

    result = send_notification(email, buy_stocks)
    return jsonify(result)


@app.route("/api/cache/clear", methods=["POST"])
def clear_cache():
    _cache.clear()
    return jsonify({"message": "キャッシュをクリアしました"})


@app.route("/favicon.ico")
def favicon():
    return "", 204


@app.route("/static/<path:filename>")
def static_files(filename):
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    return send_from_directory(static_dir, filename)


# ---------------------------------------------------------------------------
# CORS ヘッダーを全レスポンスに付与（flask-cors 未導入環境でも動作）
# ---------------------------------------------------------------------------
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
    print("=" * 50)
    print("  株価分析くん バックエンド起動中...")
    print("  ブラウザで → http://localhost:5000")
    print("  終了: Ctrl+C")
    print("=" * 50)
    app.run(
        debug=False,        # Windows で二重起動を防ぐため False に
        host="0.0.0.0",
        port=5000,
        threaded=True,
    )
