"""
database.py
SQLite を使った分析結果の永続化モジュール

テーブル構成:
    scan_results  : スキャン実行ログ（実行日時・対象市場など）
    stock_results : 各銘柄の分析結果（JSON形式で保存）
"""

import sqlite3
import json
import os
from datetime import datetime

# Render の Persistent Disk にマウントされるパスを優先、なければローカル
DB_DIR  = os.environ.get("DB_DIR", os.path.dirname(__file__))
DB_PATH = os.path.join(DB_DIR, "kabuka.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """テーブルが存在しなければ作成する（アプリ起動時に1回呼ぶ）"""
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS scan_runs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                market      TEXT    NOT NULL,
                executed_at TEXT    NOT NULL,
                total       INTEGER NOT NULL,
                buy_count   INTEGER NOT NULL,
                watch_count INTEGER NOT NULL,
                avg_yield   REAL    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS stock_results (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id      INTEGER NOT NULL REFERENCES scan_runs(id),
                code        TEXT    NOT NULL,
                ticker      TEXT    NOT NULL,
                name        TEXT    NOT NULL,
                market      TEXT    NOT NULL,
                sector      TEXT,
                score       INTEGER NOT NULL,
                buy_signal  TEXT,
                price       REAL,
                div_yield   REAL,
                data_json   TEXT    NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_stock_run ON stock_results(run_id);
            CREATE INDEX IF NOT EXISTS idx_stock_code ON stock_results(code);
        """)
    print(f"[DB] 初期化完了: {DB_PATH}")


# ---------------------------------------------------------------------------
# 書き込み
# ---------------------------------------------------------------------------
def save_scan_result(market: str, stocks_data: list[dict]) -> int:
    """
    スキャン結果を保存し、run_id を返す。
    stocks_data: fetch_stocks_parallel() の返り値（各銘柄の dict）
    """
    n          = len(stocks_data)
    buy_count  = sum(1 for s in stocks_data if s.get("buy_signal") == "今すぐ買い")
    watch_count= sum(1 for s in stocks_data if s.get("buy_signal") == "要注目")
    avg_yield  = round(sum(s.get("dividend_yield", 0) for s in stocks_data) / n, 2) if n else 0
    executed_at= datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO scan_runs
               (market, executed_at, total, buy_count, watch_count, avg_yield)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (market, executed_at, n, buy_count, watch_count, avg_yield)
        )
        run_id = cur.lastrowid

        rows = [
            (
                run_id,
                s.get("code", ""),
                s.get("ticker", ""),
                s.get("name", ""),
                s.get("market", ""),
                s.get("sector", ""),
                s.get("score", 0),
                s.get("buy_signal", ""),
                s.get("price"),
                s.get("dividend_yield"),
                json.dumps(s, ensure_ascii=False),
            )
            for s in stocks_data
        ]
        conn.executemany(
            """INSERT INTO stock_results
               (run_id, code, ticker, name, market, sector,
                score, buy_signal, price, div_yield, data_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            rows,
        )

    print(f"[DB] 保存完了: run_id={run_id}, market={market}, {n}銘柄")
    return run_id


# ---------------------------------------------------------------------------
# 読み込み
# ---------------------------------------------------------------------------
def get_latest_run(market: str = "nikkei225") -> dict | None:
    """指定市場の最新スキャン実行情報を返す"""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM scan_runs WHERE market=? ORDER BY id DESC LIMIT 1",
            (market,)
        ).fetchone()
    return dict(row) if row else None


def get_latest_stocks(
    market: str = "nikkei225",
    sector: str = "all",
    min_yield: float = 0.0,
    limit: int | None = None,
) -> tuple[dict | None, list[dict]]:
    """
    最新スキャン実行の銘柄一覧を返す。
    Returns: (run_info, stocks_list)
    """
    run = get_latest_run(market)
    if not run:
        return None, []

    sql = "SELECT data_json FROM stock_results WHERE run_id=?"
    params: list = [run["id"]]

    if sector != "all":
        sql += " AND sector=?"
        params.append(sector)

    if min_yield > 0:
        sql += " AND div_yield>=?"
        params.append(min_yield)

    sql += " ORDER BY score DESC"

    if limit:
        sql += f" LIMIT {limit}"

    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()

    stocks = [json.loads(r["data_json"]) for r in rows]
    return run, stocks


def get_stock_latest(code: str) -> dict | None:
    """指定コードの最新データを返す"""
    with get_connection() as conn:
        row = conn.execute(
            """SELECT sr.data_json
               FROM stock_results sr
               JOIN scan_runs r ON sr.run_id = r.id
               WHERE sr.code=?
               ORDER BY r.id DESC LIMIT 1""",
            (code,)
        ).fetchone()
    return json.loads(row["data_json"]) if row else None


def get_run_history(limit: int = 30) -> list[dict]:
    """実行履歴一覧（新しい順）"""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM scan_runs ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]
