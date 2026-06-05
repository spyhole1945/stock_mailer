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

# ── Claude API ───────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL      = "claude-sonnet-4-20250514"

# ── 仓位参考阈值（QQQ PE 为核心信号）────────────────────
# 根据自身风险偏好可调整
POSITION_RULES = {
    # (pe_min, pe_max): (仓位%, 风险等级, 描述)
    (0,   22): (90, "低估",   "估值偏低，可重仓持有"),
    (22,  28): (70, "合理",   "估值合理，标准仓位"),
    (28,  35): (50, "偏高",   "估值偏高，控制仓位"),
    (35,  45): (30, "高估",   "明显高估，轻仓防守"),
    (45, 999): (10, "极度高估","极度高估，保留底仓或观望"),
}
