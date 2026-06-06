import os

# ── 股票标的 ─────────────────────────────────────────────
ETF_SYMBOLS = ["QQQ", "SPY"]

STOCK_SYMBOLS = ["NVDA", "AAPL", "MSFT"]   # 可自行增删

ALL_SYMBOLS = ETF_SYMBOLS + STOCK_SYMBOLS

# ── 163 邮箱 SMTP ────────────────────────────────────────
EMAIL_SENDER   = os.environ.get("EMAIL_SENDER", "your_account@163.com")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "")   # 163 授权码，非登录密码
EMAIL_RECEIVER = os.environ.get("EMAIL_RECEIVER", "your_account@163.com")

SMTP_HOST = "smtp.163.com"
SMTP_PORT = 465   # SSL

# ── DeepSeek API ─────────────────────────────────────────
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL   = "deepseek-chat"

# ── 仓位参考阈值（QQQ PE 为核心信号）────────────────────
# 根据自身风险偏好可调整
'''
print("这段代码被注释了")
POSITION_RULES = {
    # (pe_min, pe_max): (仓位%, 风险等级, 描述)
    (0,   22): (90, "低估",   "估值偏低，可重仓持有"),
    (22,  28): (70, "合理",   "估值合理，标准仓位"),
    (28,  35): (50, "偏高",   "估值偏高，控制仓位"),
    (35,  45): (30, "高估",   "明显高估，轻仓防守"),
    (45, 999): (10, "极度高估","极度高估，保留底仓或观望"),
}
 print("不会执行")
'''
POSITION_RULES = {
    # (pe_min, pe_max): (仓位%, 风险等级, 描述)
    (0,   20): (90, "极度低估", "接近熊市底部估值，历史罕见，可满仓"),
    (20,  25): (75, "低估",    "低于20年均值，安全区域，可重仓"),
    (25,  30): (55, "合理",    "接近历史均值区间，标准仓位"),
    (30,  38): (30, "偏高",    "高于20年均值一个标准差，轻仓防守"),
    (38, 999): (10, "极度高估", "历史泡沫警戒位，保留底仓或观望"),
}
