import os

# ── 策略一标的（行情速览 + 三层定投）────────────────────
ETF_SYMBOLS = ["QQQ", "SPY","VOO"]

STOCK_SYMBOLS = ["NVDA", "AAPL", "META"]   # 可自行增删

ALL_SYMBOLS = ETF_SYMBOLS + STOCK_SYMBOLS

# ── 策略二标的（QQQ + SPHD 双仓联动）────────────────────
S2_SYMBOLS = ["QQQ", "SPHD"]

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
POSITION_RULES = {
    # (pe_min, pe_max): (仓位%, 风险等级, 描述)
    (0,   20): (90, "极度低估", "接近熊市底部，历史罕见，可满仓"),
    (20,  25): (75, "低估",    "低于20年均值，安全区域，可重仓"),
    (25,  30): (55, "合理",    "接近历史均值区间，标准仓位"),
    (30,  38): (30, "偏高",    "高于均值一个标准差，轻仓防守"),
    (38, 999): (10, "极度高估", "历史泡沫警戒位，保留底仓或观望"),
}

# ── 三层定投策略参数 ─────────────────────────────────────
# 定投频率设置
DCA_FREQUENCY     = "monthly"   # 可选: "monthly" / "biweekly" / "weekly"
DCA_EXECUTE_DAY   = 1           # 每月第几日执行（monthly 模式有效，1 = 每月1日）
#                                 biweekly: 每隔14天; weekly: 每周一

# 每月总预算分配比例
DCA_LAYER1_RATIO = 0.50   # 第一层：基础定投，无条件执行
DCA_LAYER2_RATIO = 0.30   # 第二层：估值增强，根据 PE 调整
DCA_LAYER3_RATIO = 0.20   # 第三层：极端机会，大跌时动用

# 第二层：PE 对应的投入系数（乘以该层预算）
DCA_LAYER2_PE_MULTIPLIER = {
    # (pe_min, pe_max): 投入系数
    (0,   20): 2.0,   # 极度低估：双倍加码
    (20,  25): 1.5,   # 低估：超配
    (25,  30): 1.0,   # 合理：标准投入
    (30,  35): 0.5,   # 偏高：减半
    (35,  38): 0.3,   # 高估：少量
    (38, 999): 0.0,   # 极度高估：暂停第二层
}

# 第三层：触发条件（QQQ 距52周高点回撤幅度）
DCA_LAYER3_TRIGGERS = [
    (-15, 1.0, "回撤15%：动用第三层全额"),
    (-20, 2.0, "回撤20%：动用第三层双倍"),
    (-30, 3.0, "回撤30%：动用第三层三倍（极端机会）"),
]

# QQQ 占总资产上限（超过则暂停定投，等待再平衡）
QQQ_POSITION_CAP = 0.40   # 40%

# 止盈参考线
DCA_TAKE_PROFIT_PE = 38   # PE 超过此值，考虑减仓但不全退

# ── 每月定投预算（美元）──────────────────────────────────
DCA_MONTHLY_BUDGET = 3000   # 修改为你的实际月度预算

# ══════════════════════════════════════════════════════════
# 策略二：QQQ + SPHD 双仓联动参数
# ══════════════════════════════════════════════════════════

# 初始仓位比例
S2_QQQ_INIT  = 0.50   # QQQ 初始仓位 50%
S2_SPHD_INIT = 0.50   # SPHD 初始仓位 50%

# 月度定投金额（美元）
S2_MONTHLY_BUDGET = 3000

# ── 常规月度定投规则（根据 QQQ 折溢价）──────────────────
# (溢价下限, 溢价上限): (定投比例, 说明)
S2_PREMIUM_RULES = [
    (None, 3.0,  1.00, "溢价<3%：正常全额定投"),
    (3.0,  5.0,  0.50, "溢价3–5%：减半定投，防追高"),
    (5.0,  None, 0.00, "溢价>5%：暂停当月定投，持仓不动"),
]

# ── 阶梯跨仓补仓规则（相对年度高点跌幅）────────────────
# (跌幅触发线%, SPHD划转比例%, 说明)
S2_REBALANCE_RULES = [
    (-5,  0.15, "下跌5%：划转 SPHD 15% 至 QQQ"),
    (-10, 0.30, "下跌10%：划转 SPHD 30% 至 QQQ"),
    (-15, 0.45, "下跌15%：划转 SPHD 45% 至 QQQ"),
    (-20, 0.60, "下跌20%：划转 SPHD 60% 至 QQQ"),
    (-25, 0.75, "下跌25%：划转 SPHD 75% 至 QQQ"),
    (-30, 0.80, "下跌30%：划转 SPHD 80% 至 QQQ（上限）"),
]

# SPHD 最低保留仓位（绝不低于此值）
S2_SPHD_MIN = 0.20   # 20%

# 止盈触发：QQQ 估值历史分位数（超过此值主动减仓）
S2_TAKE_PROFIT_PERCENTILE = 90   # 历史 90% 分位
# 对应的近似 PE 参考值（用于规则引擎兜底）
S2_TAKE_PROFIT_PE = 38
