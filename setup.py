"""
setup.py  —  初回セットアップスクリプト
Chart.js をローカルの static/ フォルダにダウンロードします。
ネット接続が必要です（1回だけ実行すれば OK）。

使い方:
    python setup.py
"""
import os
import urllib.request

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(STATIC_DIR, exist_ok=True)

FILES = [
    (
        "https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js",
        os.path.join(STATIC_DIR, "chart.umd.min.js"),
    ),
]

for url, dest in FILES:
    if os.path.exists(dest):
        print(f"[skip] {os.path.basename(dest)} は既にあります")
        continue
    print(f"[DL]   {url}")
    try:
        urllib.request.urlretrieve(url, dest)
        size = os.path.getsize(dest)
        print(f"[OK]   {os.path.basename(dest)}  ({size:,} bytes)")
    except Exception as e:
        print(f"[ERR]  {e}")

print("\nセットアップ完了。python app.py で起動してください。")
