"""
analyzer.py
株価データの分析モジュール
- トレンド計算 (30/60/120/180/365日)
- 極小値（底値）検出 (1階微分符号変化 + 2階微分正 = 下に凸)
- 平滑化曲線・微分曲線の生成（チャート表示用）
- 指値推奨価格の算出（強気・確実）
- 総合スコアリング
"""

import numpy as np
from scipy.signal import argrelmin, argrelmax, savgol_filter
from scipy.ndimage import uniform_filter1d


# ---------------------------------------------------------------------------
# トレンド計算
# ---------------------------------------------------------------------------
TREND_WINDOWS = [30, 60, 120, 180, 365]


def calc_trend(closes: list[float], days: int) -> float:
    """直近 days 日間の騰落率(%)を返す。データ不足時は None。"""
    if len(closes) < days:
        return None
    start = closes[-days]
    end = closes[-1]
    if start == 0:
        return None
    return (end - start) / start * 100


def calc_all_trends(closes: list[float]) -> dict:
    return {
        f"trend_{d}d": calc_trend(closes, d)
        for d in TREND_WINDOWS
    }


# ---------------------------------------------------------------------------
# 平滑化・微分曲線の生成（チャート表示用）
# ---------------------------------------------------------------------------
def _savgol_window(n: int, base: int = 21) -> int:
    """データ長に合わせた Savitzky-Golay ウィンドウ（奇数）を返す。"""
    w = min(base, n)
    if w % 2 == 0:
        w -= 1
    return max(w, 5)


def calc_chart_curves(closes: list[float]) -> dict:
    """
    チャートに重ね描きする曲線データを返す。
    - smoothed : Savitzky-Golay 平滑化曲線（株価スケール）
    - d1       : 1階微分（平滑化後）。0ライン = 下げ止まりポイント
    - d2       : 2階微分（平滑化後）。正 = 下に凸（底値候補）
    すべて closes と同じ長さのリスト。
    """
    arr = np.array(closes, dtype=float)
    n   = len(arr)
    w   = _savgol_window(n)

    # Savitzky-Golay 平滑化（ポリノミアル次数3）
    smoothed = savgol_filter(arr, window_length=w, polyorder=3)

    # 1階微分・2階微分を同じフィルタで計算（deriv引数で微係数を取得）
    d1_raw = savgol_filter(arr, window_length=w, polyorder=3, deriv=1)
    d2_raw = savgol_filter(arr, window_length=w, polyorder=3, deriv=2)

    def _round_list(lst, dec=2):
        return [round(float(v), dec) for v in lst]

    return {
        "smoothed": _round_list(smoothed, 1),
        "d1":       _round_list(d1_raw,   3),   # 単位: 円/日
        "d2":       _round_list(d2_raw,   4),   # 単位: 円/日²
    }


# ---------------------------------------------------------------------------
# 極小値（底値）検出
# ---------------------------------------------------------------------------
def detect_local_minima(closes: list[float], order: int = 5) -> list[int]:
    """
    Savitzky-Golay 平滑化後に scipy.signal.argrelmin で極小値インデックスを返す。
    order: 前後 order 日を比較して極小とみなす幅
    """
    arr      = np.array(closes, dtype=float)
    n        = len(arr)
    w        = _savgol_window(n)
    smoothed = savgol_filter(arr, window_length=w, polyorder=3)
    minima_idx = argrelmin(smoothed, order=order)[0]
    return minima_idx.tolist()


def detect_local_maxima(closes: list[float], order: int = 5) -> list[int]:
    """極大値インデックスを返す（抵抗線推定に使用）。"""
    arr      = np.array(closes, dtype=float)
    n        = len(arr)
    w        = _savgol_window(n)
    smoothed = savgol_filter(arr, window_length=w, polyorder=3)
    maxima_idx = argrelmax(smoothed, order=order)[0]
    return maxima_idx.tolist()


def is_near_local_min(closes: list[float], window: int = 60, threshold_pct: float = 3.0) -> bool:
    if len(closes) < window:
        window = len(closes)
    recent = closes[-window:]
    minima_idx = detect_local_minima(recent, order=5)
    if not minima_idx:
        return False
    min_prices = [recent[i] for i in minima_idx]
    nearest_min = min(min_prices)
    current = closes[-1]
    return current <= nearest_min * (1 + threshold_pct / 100)


def derivative_sign_check(closes: list[float], window: int = 30) -> bool:
    """
    平滑化後の1階微分が負→正に変わり、かつ2階微分が正（下に凸）かを確認。
    """
    if len(closes) < window + 2:
        return False
    arr = np.array(closes[-window:], dtype=float)
    w   = _savgol_window(len(arr))
    d1  = savgol_filter(arr, window_length=w, polyorder=3, deriv=1)
    d2  = savgol_filter(arr, window_length=w, polyorder=3, deriv=2)

    # 直近5日 vs 前5日の平均で符号変化を判断
    split = max(len(d1) // 2, 5)
    d1_prev = float(np.mean(d1[max(0, split - 5):split]))
    d1_last = float(np.mean(d1[-5:]))
    d2_last = float(np.mean(d2[-5:]))

    sign_change = (d1_prev < 0) and (d1_last > 0)
    convex_down = d2_last > 0
    return sign_change and convex_down


# ---------------------------------------------------------------------------
# 指値推奨価格の算出
# ---------------------------------------------------------------------------
def calc_limit_prices(closes: list[float]) -> dict:
    """
    長期保有向け指値推奨価格を2段階で算出する。

    【強気の指値】
        直近の極小値群の平均 × 0.98
        → 底値付近に乗れる積極的な指値

    【確実な指値】
        直近の極小値群の最安値 × 0.97
        → より深い押し目を狙う保守的な指値
        ただし 52週安値を下回らないようにクランプ

    Returns
    -------
    {
        "aggressive": float,   # 強気
        "safe":       float,   # 確実
        "basis":      str,     # 算出根拠の説明
        "support":    float,   # サポートライン（直近極小値の平均）
        "resistance": float,   # レジスタンスライン（直近極大値の平均）
    }
    """
    arr = np.array(closes, dtype=float)
    cur = float(arr[-1])
    n   = len(arr)

    # 全期間で極小・極大を探す（order=7 でノイズ耐性を高める）
    min_idx = detect_local_minima(closes, order=7)
    max_idx = detect_local_maxima(closes, order=7)

    # 直近 180 日以内の極小値に絞る
    recent_cutoff = max(0, n - 180)
    recent_min_prices = [closes[i] for i in min_idx if i >= recent_cutoff]

    # 極小値が見つからなければ直近 60 日の最安値を代替に使う
    if not recent_min_prices:
        window = min(60, n)
        recent_min_prices = [min(closes[-window:])]
        basis_note = "直近60日最安値を基準に算出"
    else:
        basis_note = f"直近180日内の極小値{len(recent_min_prices)}点を基準に算出"

    support    = round(float(np.mean(recent_min_prices)), 1)
    min_bottom = round(float(min(recent_min_prices)), 1)

    # 52週安値（絶対的な下限として使用）
    low52 = float(min(closes[-min(252, n):]))

    # 強気指値: サポートライン（極小値平均）の -2%
    aggressive = round(support * 0.98, 1)
    # 確実指値: 極小値の最安値の -3%（ただし52週安値の -1% を下限に）
    safe_raw   = min_bottom * 0.97
    safe       = round(max(safe_raw, low52 * 0.99), 1)

    # 抵抗線: 直近 180 日以内の極大値平均
    recent_max_prices = [closes[i] for i in max_idx if i >= recent_cutoff]
    resistance = round(float(np.mean(recent_max_prices)), 1) if recent_max_prices else round(cur * 1.10, 1)

    return {
        "aggressive": aggressive,
        "safe":       safe,
        "support":    support,
        "resistance": resistance,
        "basis":      basis_note,
        "low52":      round(low52, 1),
    }


# ---------------------------------------------------------------------------
# 総合スコアリング (0〜100点)
# ---------------------------------------------------------------------------
def score_stock(
    closes: list[float],
    dividend_yield: float,
    trends: dict,
) -> dict:
    """
    returns: {"score": int, "signals": list[str], "buy_signal": str}
    """
    score = 0
    signals = []

    # 1. 配当利回りスコア (最大 30点)
    if dividend_yield >= 5.0:
        score += 30; signals.append("高配当(5%以上)")
    elif dividend_yield >= 4.0:
        score += 25; signals.append("高配当(4%以上)")
    elif dividend_yield >= 3.0:
        score += 18; signals.append("中配当(3%以上)")
    elif dividend_yield >= 2.0:
        score += 10; signals.append("配当あり(2%以上)")
    elif dividend_yield >= 1.0:
        score += 5

    # 2. 極小値 / 底値検出スコア (最大 35点)
    if len(closes) >= 30:
        if derivative_sign_check(closes, window=30):
            score += 20; signals.append("底値圏(微分符号変化)")
        if is_near_local_min(closes, window=60):
            score += 15; signals.append("直近60日の極小値付近")

    # 3. トレンドスコア (最大 20点)
    t365 = trends.get("trend_365d")
    t60  = trends.get("trend_60d")
    t30  = trends.get("trend_30d")

    if t365 is not None and t30 is not None:
        if t365 < -5 and t30 > 0:
            score += 15; signals.append("長期下落→短期反発")
        elif t365 < 0 and t30 > 0:
            score += 8;  signals.append("下落トレンド底打ちの可能性")
        elif t30 > 0 and t60 is not None and t60 > 0:
            score += 5;  signals.append("短中期上昇トレンド")

    # 4. 割安感ボーナス (最大 15点)
    if len(closes) >= 252:
        low52 = min(closes[-252:])
        cur   = closes[-1]
        if cur <= low52 * 1.05:
            score += 15; signals.append("52週安値付近(5%以内)")
        elif cur <= low52 * 1.10:
            score += 8;  signals.append("52週安値付近(10%以内)")

    score = min(score, 100)

    if score >= 60:
        buy_signal = "今すぐ買い"
    elif score >= 40:
        buy_signal = "要注目"
    elif score >= 20:
        buy_signal = "様子見"
    else:
        buy_signal = "見送り"

    return {"score": score, "signals": signals, "buy_signal": buy_signal}
