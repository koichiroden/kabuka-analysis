"""
gunicorn_config.py
Render 上で gunicorn を使う際の設定ファイル

起動コマンド（render.yaml または Render ダッシュボードで設定）:
    gunicorn -c gunicorn_config.py app:app
"""

import multiprocessing

# ワーカー数（Render 無料プランは 1 に絞る）
workers = 1

# 1ワーカーあたりのスレッド数
threads = 4

# ポート（Render は PORT 環境変数を使用）
import os
bind = f"0.0.0.0:{os.environ.get('PORT', '5000')}"

# タイムアウト（yfinance の取得に時間がかかるため長めに設定）
timeout = 300

# gunicorn 起動時にスケジューラーを開始するフック
def on_starting(server):
    """gunicorn マスタープロセス起動時に1回だけ呼ばれる"""
    from database import init_db
    init_db()

def post_fork(server, worker):
    """ワーカープロセス生成後に呼ばれる（ワーカーごとに1回）"""
    # ワーカー0番だけスケジューラーを起動
    if worker.age == 1:
        from scheduler import start_scheduler
        start_scheduler()
        print("[gunicorn] スケジューラーをワーカー内で起動しました")
