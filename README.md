# 📈 美股每日简报

每个交易日盘后自动采集数据，通过 DeepSeek AI 分析，发送 HTML 邮件到你的邮箱。

## 邮件内容

- **行情速览**：QQQ / SPY / NVDA / AAPL / MSFT 的价格、涨跌、PE、52周区间、当前风险等级
- **市场情绪**：CNN 恐贪指数、VIX 恐慌指数、QQQ 回撤幅度
- **仓位建议**：基于 QQQ PE 的规则引擎建议 + DeepSeek AI 综合建议
- **AI 市场解读**：市场概况、QQQ 分析、个股简评
- **风险与明日关注**：风险提示、明日关注事项

## 文件结构

```
stock_mailer/
├── main.py              # 主入口
├── config.py            # 配置（标的、阈值、API Key 等）
├── fetch_data.py        # 数据采集（yfinance + CNN Fear & Greed）
├── analyze.py           # DeepSeek AI 分析
├── send_email.py        # 邮件渲染+发送（163 SMTP）
├── template.html        # 邮件 HTML 模板
├── requirements.txt     # Python 依赖
└── .github/
    └── workflows/
        └── daily.yml    # GitHub Actions 定时任务
```

---

## 部署步骤

### 第一步：创建 GitHub 仓库

1. 登录 [github.com](https://github.com)，点击右上角 **+** → **New repository**
2. 名字随意（如 `stock-mailer`），选 **Private**（私有），点击 Create
3. 上传本项目所有文件到仓库，注意 `.github/workflows/daily.yml` 需单独创建：
   - 点 **Add file** → **Create new file**
   - 文件名输入 `.github/workflows/daily.yml`（输入 `/` 会自动识别为文件夹）
   - 粘贴 `daily.yml` 内容，点击 **Commit changes**

### 第二步：开启 163 邮箱 SMTP

1. 登录 [mail.163.com](https://mail.163.com)
2. 设置 → POP3/SMTP/IMAP → 开启 **SMTP 服务**
3. 按提示发短信验证，获得一个**授权码**（不是登录密码）
4. 记下这个授权码备用

### 第三步：配置 GitHub Secrets

仓库页面：**Settings → Secrets and variables → Actions → Secrets 标签 → New repository secret**

依次添加以下 4 个（名字必须一字不差）：

| Secret 名称       | 填入内容                          |
|------------------|-----------------------------------|
| `DEEPSEEK_API_KEY` | 你的 DeepSeek API Key，从 [platform.deepseek.com](https://platform.deepseek.com) 获取 |
| `EMAIL_SENDER`    | 你的 163 邮箱，如 abc@163.com     |
| `EMAIL_PASSWORD`  | 第二步获得的**授权码**（非登录密码）|
| `EMAIL_RECEIVER`  | 接收邮件的邮箱（可与发件人相同）   |

### 第四步：手动触发测试

1. 仓库页面 → **Actions** 标签
2. 左侧选 **美股每日简报**
3. 右侧点 **Run workflow** → **Run workflow**
4. 等待约 1-2 分钟，查看运行日志是否有报错
5. 检查邮箱是否收到简报

**确认文件已正确上传的方法：**
- 打开仓库里的 `analyze.py`，搜索 `symbol_risk`，找到则说明是最新版本
- 打开 `template.html`，搜索 `当前风险`，找到则说明是最新版本

---

## 自定义

### 修改关注标的

编辑 `config.py`：
```python
ETF_SYMBOLS   = ["QQQ", "SPY"]
STOCK_SYMBOLS = ["NVDA", "AAPL", "MSFT"]  # 改成你想关注的股票
```

注意：如果修改了个股列表，同步修改 `analyze.py` 中 prompt 里 `stocks_comment` 和 `symbol_risk` 的股票名称，否则 AI 仍会按旧列表分析。

### 修改仓位阈值

编辑 `config.py` 中的 `POSITION_RULES`，基于 QQQ PE 的建议仓位参考：

| QQQ PE 区间 | 建议仓位 | 历史含义 |
|------------|---------|---------|
| < 20       | 90%     | 接近熊市底部，历史罕见 |
| 20 – 25    | 75%     | 低于20年均值，安全区 |
| 25 – 30    | 55%     | 接近历史均值，合理区 |
| 30 – 38    | 30%     | 高于均值一个标准差，偏贵 |
| > 38       | 10%     | 历史泡沫警戒位 |

### 修改发送时间

编辑 `.github/workflows/daily.yml` 中的 cron 表达式：
```yaml
- cron: '0 21 * * 1-5'   # UTC 21:00 = 美东 17:00（夏令时，3-11月）
```

冬令时（11月-次年3月）需改为：
```yaml
- cron: '0 22 * * 1-5'   # UTC 22:00 = 美东 17:00（冬令时）
```

---

## 费用估算

| 项目             | 费用                            |
|-----------------|---------------------------------|
| GitHub Actions  | 免费（每月 2000 分钟）           |
| 163 邮箱 SMTP   | 免费                            |
| yfinance 数据   | 免费                            |
| DeepSeek API    | ~$0.002 / 天（约¥0.5/月）       |

---

## 常见问题

**Q: 邮件发送失败，报 535 错误？**
A: 163 授权码有误，重新到邮箱设置页获取，注意是授权码不是登录密码。

**Q: yfinance 报 `No data found`？**
A: Yahoo Finance 偶尔限流，等 5 分钟后在 Actions 页面手动重新触发一次。

**Q: Actions 运行成功但"当前风险"列显示 `—`？**
A: 说明仓库里的 `analyze.py` 或 `template.html` 还是旧版本，按第四步的方法确认文件内容后重新上传。

**Q: 如何确认 GitHub 上是最新文件？**
A: 打开仓库文件，查看右上角的 commit 时间。若时间是刚刚，且文件内能搜到关键词（`symbol_risk` / `当前风险`），则为最新版本。

**Q: 非交易日会发邮件吗？**
A: 会，但数据为最近一个交易日的数据。如需彻底跳过，可在 `main.py` 开头加以下代码：
```python
import datetime
if datetime.datetime.now().weekday() >= 5:
    print("今日为周末，跳过运行")
    sys.exit(0)
```

---

*本工具仅供个人学习参考，不构成任何投资建议。*
