# 📈 美股每日简报

每个交易日盘后自动采集数据，通过 Claude AI 分析，发送 HTML 邮件到你的邮箱。

## 文件结构

```
stock_mailer/
├── main.py              # 主入口
├── config.py            # 配置（标的、阈值等）
├── fetch_data.py        # 数据采集
├── analyze.py           # Claude AI 分析
├── send_email.py        # 邮件渲染+发送
├── template.html        # 邮件 HTML 模板
├── requirements.txt     # 依赖
└── .github/
    └── workflows/
        └── daily.yml    # GitHub Actions 定时任务
```

---

## 部署步骤

### 第一步：创建 GitHub 仓库

1. 登录 [github.com](https://github.com)，点击右上角 **+** → **New repository**
2. 名字随意（如 `stock-mailer`），选 **Private**（私有），点击 Create
3. 把本项目所有文件上传到仓库（保持目录结构）

### 第二步：开启 163 邮箱 SMTP

1. 登录 [mail.163.com](https://mail.163.com)
2. 设置 → POP3/SMTP/IMAP → 开启 **SMTP 服务**
3. 按提示发短信验证，获得一个**授权码**（不是登录密码）
4. 记下这个授权码

### 第三步：配置 GitHub Secrets

在你的仓库页面：**Settings → Secrets and variables → Actions → New repository secret**

依次添加以下 4 个：

| Secret 名称         | 填入内容                        |
|--------------------|---------------------------------|
| `ANTHROPIC_API_KEY` | 你的 Claude API Key             |
| `EMAIL_SENDER`      | 你的 163 邮箱，如 abc@163.com   |
| `EMAIL_PASSWORD`    | 上一步获得的**授权码**           |
| `EMAIL_RECEIVER`    | 接收邮件的邮箱（可以和发件人一样）|

### 第四步：手动触发测试

1. 仓库页面 → **Actions** 标签
2. 左侧选 **美股每日简报**
3. 右侧点 **Run workflow** → **Run workflow**
4. 等待约 1-2 分钟，查看运行日志
5. 检查你的邮箱是否收到邮件

---

## 自定义

### 修改关注标的

编辑 `config.py`：
```python
ETF_SYMBOLS   = ["QQQ", "SPY"]
STOCK_SYMBOLS = ["NVDA", "AAPL", "MSFT"]  # 改成你想关注的股票
```

### 修改仓位阈值

```python
POSITION_RULES = {
    (0,   22): (90, "低估",   "估值偏低，可重仓持有"),
    (22,  28): (70, "合理",   "估值合理，标准仓位"),
    ...
}
```

### 修改发送时间

编辑 `.github/workflows/daily.yml` 中的 cron 表达式：
```yaml
- cron: '0 21 * * 1-5'   # UTC 时间，对应美东 17:00（夏令时）
```

冬令时（11月-次年3月）改为：
```yaml
- cron: '0 22 * * 1-5'
```

---

## 费用估算

| 项目            | 费用                          |
|----------------|-------------------------------|
| GitHub Actions  | 免费（每月 2000 分钟）         |
| 163 邮箱 SMTP   | 免费                          |
| yfinance 数据   | 免费                          |
| Claude API      | ~$0.005–0.01 / 天（约¥1/月）  |

---

## 常见问题

**Q: 邮件发送失败，报 535 错误？**
A: 163 授权码输入有误，重新到邮箱设置页获取。

**Q: yfinance 报 `No data found`？**
A: Yahoo Finance 有时限流，等 5 分钟再手动触发一次。

**Q: 如何在非交易日跳过运行？**
A: `fetch_data.py` 中已设置 `period="2d"` 拉取最新数据，非交易日数据不更新，邮件仍会发送但数据为最近一个交易日。如需彻底跳过，可在 `main.py` 加判断今天是否为工作日。

---

*本工具仅供个人学习参考，不构成任何投资建议。*
