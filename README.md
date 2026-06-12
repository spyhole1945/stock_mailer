# 📈 stock_mailer — 美股每日简报

每个交易日盘后自动采集市场数据，通过 DeepSeek AI 分析，生成 HTML 邮件发送到指定邮箱。

支持两套独立投资策略，每日一封邮件统一呈现。

---

## 目录

- [邮件内容结构](#邮件内容结构)
- [文件结构](#文件结构)
- [快速部署](#快速部署)
- [策略一：QQQ 三层估值定投](#策略一qqq-三层估值定投)
- [策略二：QQQ--SPHD-双仓联动](#策略二qqq--sphd-双仓联动)
- [参数配置速查](#参数配置速查)
- [常见问题排查](#常见问题排查)
- [费用估算](#费用估算)

---

## 邮件内容结构

```
📈 美股每日简报
│
├── ── 策略一：QQQ 三层估值定投 ──────────────────
│   ├── 📊 行情速览        QQQ/SPY/NVDA/AAPL/MSFT 价格、涨跌、PE、当前风险等级
│   ├── 🌡️ 市场情绪        CNN 恐贪指数 / VIX / QQQ 52周回撤进度条
│   ├── ⚖️ 仓位建议        基于 PE 的规则引擎建议 + DeepSeek AI 综合建议
│   ├── 💰 本期定投建议    三层计算结果（含 QQQ 采集价格、各层金额、本期合计）
│   └── 🤖 AI 市场解读     市场概况 / QQQ 分析 / 个股简评 / 风险提示 / 明日关注
│
└── ── 策略二：QQQ + SPHD 双仓联动 ───────────────
    ├── 📊 双仓标的行情    QQQ（进攻仓）/ SPHD（防守仓）年度跌幅 / 折溢价
    └── 📋 今日执行清单    4项决策（止盈/跨仓调仓/月度定投/修复回归）+ 具体金额
```

---

## 文件结构

```
stock_mailer/
├── main.py                 # 主入口，串联所有模块
├── config.py               # ⭐ 所有参数配置（标的、预算、阈值等）
├── fetch_data.py           # 数据采集（yfinance + CNN Fear & Greed）
├── dca_engine.py           # 策略一计算引擎（三层定投）
├── strategy2_engine.py     # 策略二计算引擎（QQQ+SPHD双仓）
├── analyze.py              # DeepSeek AI 分析
├── send_email.py           # Jinja2 渲染 + 163 SMTP 发送
├── template.html           # 邮件 HTML 模板
├── requirements.txt        # Python 依赖
└── .github/
    └── workflows/
        └── daily.yml       # GitHub Actions 定时任务
```

### 各模块职责说明

| 文件 | 职责 | 修改场景 |
|------|------|---------|
| `config.py` | 所有可配置参数 | 改预算、改标的、改阈值 |
| `fetch_data.py` | 从 Yahoo Finance / CNN 拉取数据 | 新增数据源、修复采集报错 |
| `dca_engine.py` | 策略一三层定投逻辑计算 | 调整定投层比例或触发规则 |
| `strategy2_engine.py` | 策略二双仓联动逻辑计算 | 调整调仓阈值或定投规则 |
| `analyze.py` | 构建 prompt + 调用 DeepSeek | 修改 AI 分析角度或字段 |
| `send_email.py` | 渲染模板 + SMTP 发送 | 修复邮件发送问题 |
| `template.html` | 邮件 HTML 视觉呈现 | 调整布局或新增展示字段 |
| `daily.yml` | 定时触发时间 | 修改发送时间 |

---

## 快速部署

### 第一步：创建 GitHub 私有仓库

1. 登录 [github.com](https://github.com)，右上角 **+** → **New repository**
2. 名称任意（如 `stock-mailer`），选 **Private**，点击 Create
3. 上传所有文件，注意 `.github/workflows/daily.yml` 需单独创建：
   - 点 **Add file** → **Create new file**
   - 文件名输入 `.github/workflows/daily.yml`（输入 `/` 自动创建子目录）
   - 粘贴 `daily.yml` 内容 → **Commit changes**

### 第二步：开启 163 邮箱 SMTP

1. 登录 [mail.163.com](https://mail.163.com)
2. 设置 → POP3/SMTP/IMAP → 开启 **SMTP 服务**
3. 按提示发短信验证，获得**授权码**（注意：不是登录密码）

### 第三步：配置 GitHub Secrets

仓库页面：**Settings → Secrets and variables → Actions → Secrets 标签 → New repository secret**

| Secret 名称 | 内容 | 说明 |
|------------|------|------|
| `DEEPSEEK_API_KEY` | `sk-xxxx...` | 从 [platform.deepseek.com](https://platform.deepseek.com) 获取 |
| `EMAIL_SENDER` | `abc@163.com` | 163 发件邮箱 |
| `EMAIL_PASSWORD` | `xxxxxx` | 163 **授权码**，非登录密码 |
| `EMAIL_RECEIVER` | `abc@163.com` | 收件邮箱（可与发件人相同） |

### 第四步：测试运行

1. 仓库页面 → **Actions** 标签
2. 左侧选 **美股每日简报**
3. 右侧点 **Run workflow** → **Run workflow**
4. 约 2 分钟后查看运行日志，确认邮箱是否收到邮件

**验证文件版本正确的方法：**
- 打开仓库 `analyze.py`，搜索 `s2_comment` → 找到则为最新版
- 打开 `template.html`，搜索 `策略二` → 找到则为最新版
- 打开 `send_email.py`，搜索 `DotDict` → 找到则为最新版

---

## 策略一：QQQ 三层估值定投

### 核心思路

根据 QQQ 当前 PE 决定投入比例，分三层执行，避免在高估时满仓、低估时空仓。

### 三层结构

```
月度预算（$3000）
├── 第一层 50%（$1500）：无条件执行，每月固定买入
├── 第二层 30%（$900） ：根据 QQQ PE 打折执行
└── 第三层 20%（$600） ：仅在 QQQ 大幅回撤时触发
```

### 第二层 PE 系数

| QQQ PE | 投入系数 | 实际投入（基于$900） |
|--------|---------|-------------------|
| < 20   | 2.0x    | $1800（超配）      |
| 20–25  | 1.5x    | $1350（加码）      |
| 25–30  | 1.0x    | $900（标准）       |
| 30–35  | 0.5x    | $450（缩减）       |
| 35–38  | 0.3x    | $270（少量）       |
| > 38   | 0x      | $0（暂停）         |

### 第三层触发条件

基于 QQQ 距 **52周最高点** 的回撤幅度：

| 回撤幅度 | 额外投入倍数 | 实际追加（基于$600） |
|---------|------------|-------------------|
| ≥ 15%  | 1x         | $600              |
| ≥ 20%  | 2x         | $1200             |
| ≥ 30%  | 3x         | $1800             |

### 情绪修正

CNN 恐贪指数会对总投入做额外修正：

| 恐贪指数 | 修正系数 |
|---------|---------|
| ≥ 80（极度贪婪） | ×0.70 缩减 |
| 65–80（贪婪）    | ×0.85 小幅缩减 |
| 35–65（中性）    | ×1.00 不变 |
| 20–35（恐惧）    | ×1.10 小幅加码 |
| ≤ 20（极度恐惧） | ×1.20 加码 |

### 仓位参考阈值（基于 QQQ 20年历史 PE）

| QQQ PE | 建议仓位 | 历史含义 |
|--------|---------|---------|
| < 20   | 90%     | 接近熊市底部，历史罕见（如2011年底） |
| 20–25  | 75%     | 低于20年均值(22.5)，安全区 |
| 25–30  | 55%     | 接近历史均值，合理区 |
| 30–38  | 30%     | 高于均值一个标准差，偏贵 |
| > 38   | 10%     | 历史泡沫警戒位（如2020、2024年底） |

### 定投频率配置

在 `config.py` 修改：

```python
DCA_FREQUENCY   = "monthly"   # monthly / biweekly / weekly
DCA_EXECUTE_DAY = 1           # 每月第几日（monthly 模式）
```

邮件会自动显示"今天是操作日"或"距下次操作日 X 天"。

---

## 策略二：QQQ + SPHD 双仓联动

### 核心思路

QQQ（进攻仓）和 SPHD（防守仓）各持 50%，利用 SPHD 的高股息稳定性在 QQQ 大跌时提供弹药，跌得越深补得越多，回升后再恢复平衡。

### 四项每日决策

**决策1：本月定投多少（看 QQQ 折溢价）**

| QQQ 折溢价 | 操作 | 金额 |
|-----------|------|------|
| < 3%（正常） | 全额定投 | $3000 |
| 3–5%（略高） | 减半定投 | $1500 |
| > 5%（过热） | 暂停定投 | $0 |

**决策2：是否跨仓补仓（看年度高点跌幅）**

基准为**当年1月起的最高收盘价**：

| 跌幅 | 从 SPHD 划转至 QQQ |
|------|-------------------|
| ≥ 5%  | SPHD 的 15% |
| ≥ 10% | SPHD 的 30% |
| ≥ 15% | SPHD 的 45% |
| ≥ 20% | SPHD 的 60% |
| ≥ 25% | SPHD 的 75% |
| ≥ 30% | SPHD 的 80%（上限，停止继续调仓） |

> ⚠️ 铁律：SPHD 底仓最低保留 20%，任何情况下不得低于此值。

**决策3：是否止盈（看 QQQ PE）**

PE ≥ 38（历史90%分位）时，建议减仓 QQQ 10–20%，资金转入 SPHD 锁定收益。

**决策4：是否修复回归**

QQQ 回升至年度高点 1% 以内时，将超额 QQQ 仓位逐步转回 SPHD，恢复 5:5 基准配比。

### 年度再平衡

每年 12 月底执行一次：
1. 将 QQQ/SPHD 恢复至 5:5 配比
2. 更新次年「年度最高点」基准为最新收盘价

---

## 参数配置速查

所有参数集中在 `config.py`，日常维护只需改这一个文件：

```python
# ── 修改关注标的 ──────────────────────────────
ETF_SYMBOLS   = ["QQQ", "SPY"]
STOCK_SYMBOLS = ["NVDA", "AAPL", "MSFT"]  # 增删个股改这里

# ── 修改策略一月预算 ──────────────────────────
DCA_MONTHLY_BUDGET = 3000   # 美元

# ── 修改策略一定投频率 ────────────────────────
DCA_FREQUENCY   = "monthly"   # monthly / biweekly / weekly
DCA_EXECUTE_DAY = 1           # 每月第几日

# ── 修改策略二月预算 ──────────────────────────
S2_MONTHLY_BUDGET = 3000   # 美元

# ── 修改策略二跨仓阈值 ────────────────────────
S2_REBALANCE_RULES = [
    (-5,  0.15, "下跌5%：划转 SPHD 15% 至 QQQ"),
    ...
]
```

> 注意：修改 `STOCK_SYMBOLS` 后，需同步修改 `analyze.py` prompt 里的个股名称和 `symbol_risk` 字段，否则 AI 仍按旧列表分析。

### 修改发送时间

编辑 `.github/workflows/daily.yml`：

```yaml
# 美东时间 17:00 发送（UTC）
- cron: '0 21 * * 1-5'   # 夏令时（3月–11月）
- cron: '0 22 * * 1-5'   # 冬令时（11月–次年3月）
```

---

## 常见问题排查

**Q: Actions 运行报错 `UndefinedError: 'dict object' has no attribute 'xxx'`**

A: `send_email.py` 版本过旧，确认文件里有 `DotDict` 类定义（搜索关键词），没有则重新上传最新版。

**Q: 邮件发送失败，报 535 错误**

A: 163 授权码有误。重新到 163 邮箱设置页获取授权码，注意是授权码不是登录密码，重新填入 GitHub Secret `EMAIL_PASSWORD`。

**Q: yfinance 报 `No data found` 或数据为 None**

A: Yahoo Finance 偶尔限流。在 Actions 页面手动重新触发一次即可。如频繁出现，可在 `fetch_data.py` 的 `fetch_quote()` 里增加 `time.sleep(1)` 减缓请求频率。

**Q: AI 分析部分显示"AI 分析失败"**

A: DeepSeek API Key 失效或余额不足。登录 [platform.deepseek.com](https://platform.deepseek.com) 检查余额和 Key 状态，重新填入 GitHub Secret `DEEPSEEK_API_KEY`。

**Q: 策略二"当前风险"或"执行清单"显示异常**

A: 检查以下文件版本：
- `strategy2_engine.py` 是否存在（新文件，首次部署需单独上传）
- `send_email.py` 里搜索 `DotDict` 确认为最新版
- `fetch_data.py` 里搜索 `fetch_qqq_annual_drawdown` 确认为最新版

**Q: 如何确认 GitHub 上的文件是最新版本？**

A: 打开仓库文件，查看右上角 commit 时间。关键词验证：
- `analyze.py` → 搜索 `s2_comment`
- `template.html` → 搜索 `策略二`
- `send_email.py` → 搜索 `DotDict`
- `strategy2_engine.py` → 搜索 `get_recovery_status`

**Q: 非交易日是否会发邮件？**

A: 会，但数据为最近一个交易日。如需周末跳过，在 `main.py` 开头加：

```python
import datetime
if datetime.datetime.now().weekday() >= 5:
    print("今日为周末，跳过运行")
    sys.exit(0)
```

---

## 费用估算

| 项目 | 费用 |
|------|------|
| GitHub Actions | 免费（每月 2000 分钟，本项目每天约用 2 分钟） |
| 163 邮箱 SMTP | 免费 |
| yfinance / CNN 数据 | 免费 |
| DeepSeek API | 约 $0.002 / 天，约 $0.05 / 月 |

充值 $5 可使用约 8 年。

---

*本项目仅供个人学习参考，不构成任何投资建议。*
