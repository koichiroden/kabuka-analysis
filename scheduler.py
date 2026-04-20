"""
scheduler.py
APScheduler を使い、毎日平日15:35（JST）に分析を自動実行してDBへ保存する。

・Flask アプリと同一プロセスで動作
・手動実行 API (/api/admin/run_scan) でもトリガー可能
"""

import os
import time
import threading
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

from stocks import ALL_STOCKS
from database import init_db, save_scan_result

JST = pytz.timezone("Asia/Tokyo")

# 実行中フラグ（重複実行防止）
_running = threading.Lock()


def run_daily_scan(market: str = "all"):
    """
    全銘柄（または指定市場）を分析してDBに保存する。
    app.py の fetch_stocks_parallel を使い回す。
    """
    # ここでのインポートは循環参照を避けるため関数内で行う
    from app import fetch_stocks_parallel

    if not _running.acquire(blocking=False):
        print("[Scheduler] 前回のスキャンがまだ実行中のためスキップします")
        return

    try:
        start = datetime.now(JST)
        print(f"[Scheduler] スキャン開始: {start.strftime('%Y-%m-%d %H:%M:%S JST')}")

        targets = ALL_STOCKS if market == "all" else [s for s in ALL_STOCKS if s["market"] == market]

        # ── nikkei225 と growth を別々に保存する ──────────────────────────
        for mkt in ["nikkei225", "growth"]:
            mkt_targets = [s for s in targets if s["market"] == mkt]
            if not mkt_targets:
                continue

            print(f"[Scheduler] {mkt}: {len(mkt_targets)}銘柄を取得中...")
            stocks_data = fetch_stocks_parallel(mkt_targets)
            stocks_data.sort(key=lambda x: x["score"], reverse=True)
            save_scan_result(mkt, stocks_data)
            print(f"[Scheduler] {mkt}: 完了 ({len(stocks_data)}銘柄)")

        elapsed = (datetime.now(JST) - start).seconds
        print(f"[Scheduler] スキャン完了: {elapsed}秒")

    except Exception as e:
        print(f"[Scheduler] エラー: {e}")
    finally:
        _running.release()


def start_scheduler():
    """Flask 起動時に呼び出す。スケジューラーをバックグラウンドで起動。"""
    init_db()

    scheduler = BackgroundScheduler(timezone=JST)

    # 平日（月〜金）15:35 JST に実行
    # 東京証券取引所は15:30クローズ → 5分後に取得
    scheduler.add_job(
        func=run_daily_scan,
        trigger=CronTrigger(
            day_of_week="mon-fri",
            hour=15,
            minute=35,
            timezone=JST,
        ),
        id="daily_scan",
        name="毎日定時スキャン",
        replace_existing=True,
        kwargs={"market": "all"},
    )

    scheduler.start()
    print("[Scheduler] バックグラウンドスケジューラー起動: 平日15:35 JSTに自動実行")
    return scheduler
