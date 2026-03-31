"""
notifier.py
お買い得銘柄をメールで通知するモジュール。
Gmailの場合はアプリパスワードを使用してください。
"""

import smtplib
import json
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime


# ---------------------------------------------------------------------------
# 設定 (環境変数 or config.json から読み込む)
# ---------------------------------------------------------------------------
def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


# ---------------------------------------------------------------------------
# メール本文生成
# ---------------------------------------------------------------------------
def build_email_body(buy_stocks: list[dict], scan_date: str) -> str:
    lines = [
        f"【株価分析くん】お買い得銘柄通知 - {scan_date}",
        "=" * 50,
        f"本日のスキャンで {len(buy_stocks)} 件の買い時銘柄が見つかりました。",
        "",
    ]

    for i, s in enumerate(buy_stocks, 1):
        trends = s.get("trends", {})
        trend_str = " / ".join([
            f"{k.replace('trend_','').replace('d','日')}: {v:+.1f}%"
            for k, v in trends.items() if v is not None
        ])
        lines += [
            f"【{i}位】{s['name']} ({s['code']}) [{s['sector']}]",
            f"  現在値    : ¥{s['price']:,.0f}",
            f"  配当利回り: {s['dividend_yield']:.1f}%",
            f"  総合スコア: {s['score']}点 ({s['buy_signal']})",
            f"  シグナル  : {', '.join(s.get('signals', []))}",
            f"  トレンド  : {trend_str}",
            "",
        ]

    lines += [
        "-" * 50,
        "※ 本メールは株価分析くんの自動通知です。",
        "※ 投資は自己責任でお願いします。",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# メール送信
# ---------------------------------------------------------------------------
def send_notification(
    to_email: str,
    buy_stocks: list[dict],
    smtp_host: str = None,
    smtp_port: int = 587,
    smtp_user: str = None,
    smtp_pass: str = None,
) -> dict:
    """
    Parameters
    ----------
    to_email   : 送信先メールアドレス
    buy_stocks : 買い時銘柄リスト
    smtp_*     : SMTP設定 (省略時は config.json から読み込む)

    Returns
    -------
    {"success": bool, "message": str}
    """
    config = load_config()
    smtp_host = smtp_host or config.get("smtp_host", "smtp.gmail.com")
    smtp_port = smtp_port or config.get("smtp_port", 587)
    smtp_user = smtp_user or config.get("smtp_user", "")
    smtp_pass = smtp_pass or config.get("smtp_pass", "")

    if not smtp_user or not smtp_pass:
        return {
            "success": False,
            "message": "SMTP設定が未完了です。config.json を確認してください。"
        }

    if not buy_stocks:
        return {"success": True, "message": "買い時銘柄なし、メール送信をスキップしました。"}

    scan_date = datetime.now().strftime("%Y年%m月%d日")
    body = build_email_body(buy_stocks, scan_date)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"【株価分析くん】{len(buy_stocks)}件の買い時銘柄 - {scan_date}"
    msg["From"]    = smtp_user
    msg["To"]      = to_email
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, to_email, msg.as_string())
        return {"success": True, "message": f"{to_email} に送信しました。"}
    except Exception as e:
        return {"success": False, "message": f"送信エラー: {str(e)}"}
