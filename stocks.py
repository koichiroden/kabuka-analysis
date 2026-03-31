# 銘柄マスターリスト
# Yahoo Finance のティッカーは日本株は「コード.T」形式

NIKKEI225 = [
    # 製造業
    {"code": "7203", "ticker": "7203.T", "name": "トヨタ自動車",        "sector": "製造業", "industry": "自動車"},
    {"code": "7267", "ticker": "7267.T", "name": "本田技研工業",        "sector": "製造業", "industry": "自動車"},
    {"code": "7269", "ticker": "7269.T", "name": "スズキ",              "sector": "製造業", "industry": "自動車"},
    {"code": "7270", "ticker": "7270.T", "name": "SUBARU",             "sector": "製造業", "industry": "自動車"},
    {"code": "7201", "ticker": "7201.T", "name": "日産自動車",          "sector": "製造業", "industry": "自動車"},
    {"code": "6758", "ticker": "6758.T", "name": "ソニーグループ",      "sector": "製造業", "industry": "電機"},
    {"code": "6861", "ticker": "6861.T", "name": "キーエンス",          "sector": "製造業", "industry": "電機"},
    {"code": "6902", "ticker": "6902.T", "name": "デンソー",            "sector": "製造業", "industry": "自動車部品"},
    {"code": "6954", "ticker": "6954.T", "name": "ファナック",          "sector": "製造業", "industry": "機械"},
    {"code": "6301", "ticker": "6301.T", "name": "小松製作所",          "sector": "製造業", "industry": "機械"},
    {"code": "6367", "ticker": "6367.T", "name": "ダイキン工業",        "sector": "製造業", "industry": "機械"},
    {"code": "7741", "ticker": "7741.T", "name": "HOYA",               "sector": "製造業", "industry": "精密機器"},
    {"code": "7733", "ticker": "7733.T", "name": "オリンパス",          "sector": "製造業", "industry": "精密機器"},
    {"code": "6971", "ticker": "6971.T", "name": "京セラ",              "sector": "製造業", "industry": "電子部品"},
    {"code": "6981", "ticker": "6981.T", "name": "村田製作所",          "sector": "製造業", "industry": "電子部品"},
    {"code": "6762", "ticker": "6762.T", "name": "TDK",                "sector": "製造業", "industry": "電子部品"},
    # 通信
    {"code": "9432", "ticker": "9432.T", "name": "日本電信電話(NTT)",   "sector": "通信",   "industry": "通信"},
    {"code": "9433", "ticker": "9433.T", "name": "KDDI",               "sector": "通信",   "industry": "通信"},
    {"code": "9434", "ticker": "9434.T", "name": "ソフトバンク",        "sector": "通信",   "industry": "通信"},
    {"code": "9984", "ticker": "9984.T", "name": "ソフトバンクグループ","sector": "通信",   "industry": "持株会社"},
    # 医療・医薬
    {"code": "4568", "ticker": "4568.T", "name": "第一三共",            "sector": "医療・医薬", "industry": "医薬品"},
    {"code": "4502", "ticker": "4502.T", "name": "武田薬品工業",        "sector": "医療・医薬", "industry": "医薬品"},
    {"code": "4507", "ticker": "4507.T", "name": "塩野義製薬",          "sector": "医療・医薬", "industry": "医薬品"},
    {"code": "4519", "ticker": "4519.T", "name": "中外製薬",            "sector": "医療・医薬", "industry": "医薬品"},
    {"code": "4523", "ticker": "4523.T", "name": "エーザイ",            "sector": "医療・医薬", "industry": "医薬品"},
    # 金融・銀行
    {"code": "8306", "ticker": "8306.T", "name": "三菱UFJフィナンシャル","sector": "金融・銀行", "industry": "銀行"},
    {"code": "8316", "ticker": "8316.T", "name": "三井住友フィナンシャル","sector": "金融・銀行", "industry": "銀行"},
    {"code": "8411", "ticker": "8411.T", "name": "みずほフィナンシャル", "sector": "金融・銀行", "industry": "銀行"},
    {"code": "8591", "ticker": "8591.T", "name": "オリックス",          "sector": "金融・銀行", "industry": "リース"},
    {"code": "8630", "ticker": "8630.T", "name": "SOMPOホールディングス","sector": "金融・銀行", "industry": "保険"},
    {"code": "8725", "ticker": "8725.T", "name": "MS&ADインシュアランス","sector": "金融・銀行", "industry": "保険"},
    # 小売・流通
    {"code": "3382", "ticker": "3382.T", "name": "セブン&アイHD",       "sector": "小売・流通","industry": "コンビニ"},
    {"code": "8267", "ticker": "8267.T", "name": "イオン",              "sector": "小売・流通","industry": "スーパー"},
    {"code": "3産", "ticker": "3086.T",  "name": "J.フロントリテイリング","sector": "小売・流通","industry": "百貨店"},
    # 食品・飲料
    {"code": "2802", "ticker": "2802.T", "name": "味の素",              "sector": "食品・飲料","industry": "食品"},
    {"code": "2503", "ticker": "2503.T", "name": "キリンホールディングス","sector": "食品・飲料","industry": "飲料"},
    {"code": "2587", "ticker": "2587.T", "name": "サントリー食品",       "sector": "食品・飲料","industry": "飲料"},
    {"code": "2914", "ticker": "2914.T", "name": "JT(日本たばこ産業)",   "sector": "食品・飲料","industry": "たばこ"},
    # 電力・ガス
    {"code": "9501", "ticker": "9501.T", "name": "東京電力HD",          "sector": "電力・ガス","industry": "電力"},
    {"code": "9503", "ticker": "9503.T", "name": "関西電力",            "sector": "電力・ガス","industry": "電力"},
    {"code": "9531", "ticker": "9531.T", "name": "東京ガス",            "sector": "電力・ガス","industry": "ガス"},
    {"code": "9532", "ticker": "9532.T", "name": "大阪ガス",            "sector": "電力・ガス","industry": "ガス"},
    # 素材・化学
    {"code": "4063", "ticker": "4063.T", "name": "信越化学工業",        "sector": "素材・化学","industry": "化学"},
    {"code": "3401", "ticker": "3401.T", "name": "帝人",               "sector": "素材・化学","industry": "繊維"},
    {"code": "4183", "ticker": "4183.T", "name": "三井化学",            "sector": "素材・化学","industry": "化学"},
    {"code": "5401", "ticker": "5401.T", "name": "日本製鉄",            "sector": "素材・化学","industry": "鉄鋼"},
    {"code": "5108", "ticker": "5108.T", "name": "ブリヂストン",        "sector": "素材・化学","industry": "ゴム"},
    # 不動産
    {"code": "8801", "ticker": "8801.T", "name": "三井不動産",          "sector": "不動産",   "industry": "不動産"},
    {"code": "8802", "ticker": "8802.T", "name": "三菱地所",            "sector": "不動産",   "industry": "不動産"},
    {"code": "8830", "ticker": "8830.T", "name": "住友不動産",          "sector": "不動産",   "industry": "不動産"},
    # 建設
    {"code": "1803", "ticker": "1803.T", "name": "清水建設",            "sector": "建設",     "industry": "建設"},
    {"code": "1801", "ticker": "1801.T", "name": "大成建設",            "sector": "建設",     "industry": "建設"},
    {"code": "1802", "ticker": "1802.T", "name": "大林組",              "sector": "建設",     "industry": "建設"},
    # IT・テック
    {"code": "4307", "ticker": "4307.T", "name": "野村総合研究所",      "sector": "IT・テック","industry": "ITサービス"},
    {"code": "9613", "ticker": "9613.T", "name": "NTTデータグループ",   "sector": "IT・テック","industry": "ITサービス"},
    {"code": "4689", "ticker": "4689.T", "name": "LINEヤフー",         "sector": "IT・テック","industry": "インターネット"},
    # 輸送・物流
    {"code": "9020", "ticker": "9020.T", "name": "東日本旅客鉄道",      "sector": "輸送・物流","industry": "鉄道"},
    {"code": "9021", "ticker": "9021.T", "name": "西日本旅客鉄道",      "sector": "輸送・物流","industry": "鉄道"},
    {"code": "9101", "ticker": "9101.T", "name": "日本郵船",            "sector": "輸送・物流","industry": "海運"},
    {"code": "9107", "ticker": "9107.T", "name": "川崎汽船",            "sector": "輸送・物流","industry": "海運"},
    {"code": "9064", "ticker": "9064.T", "name": "ヤマトホールディングス","sector": "輸送・物流","industry": "宅配"},
]

GROWTH = [
    {"code": "4385", "ticker": "4385.T", "name": "メルカリ",            "sector": "IT・テック","industry": "EC"},
    {"code": "4479", "ticker": "4479.T", "name": "マクアケ",            "sector": "IT・テック","industry": "クラウドファンディング"},
    {"code": "4565", "ticker": "4565.T", "name": "そーせいグループ",    "sector": "医療・医薬","industry": "バイオ"},
    {"code": "4478", "ticker": "4478.T", "name": "フリー",              "sector": "IT・テック","industry": "SaaS"},
    {"code": "3923", "ticker": "3923.T", "name": "ラクス",              "sector": "IT・テック","industry": "SaaS"},
    {"code": "4371", "ticker": "4371.T", "name": "コアコンセプト・T",   "sector": "IT・テック","industry": "ITコンサル"},
    {"code": "7676", "ticker": "7676.T", "name": "グッドスピード",      "sector": "小売・流通","industry": "中古車"},
    {"code": "9142", "ticker": "9142.T", "name": "九州旅客鉄道",        "sector": "輸送・物流","industry": "鉄道"},
    {"code": "4174", "ticker": "4174.T", "name": "アピリッツ",          "sector": "IT・テック","industry": "Webゲーム"},
    {"code": "4195", "ticker": "4195.T", "name": "スパイダープラス",    "sector": "IT・テック","industry": "建設DX"},
]

ALL_STOCKS = [dict(s, market="nikkei225") for s in NIKKEI225 if s.get("ticker")] + \
             [dict(s, market="growth") for s in GROWTH]

# コードが不正なエントリを除外
ALL_STOCKS = [s for s in ALL_STOCKS if s["ticker"].replace(".T","").isdigit()]
