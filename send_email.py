"""
send_email.py — Jinja2 渲染 + 163 SMTP 发送
"""
import smtplib, ssl, datetime
from email.mime.text      import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Environment, FileSystemLoader
from config import EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECEIVER, SMTP_HOST, SMTP_PORT


class DotDict:
    """让 dict 支持点号访问，供 Jinja2 模板使用"""
    def __init__(self, d: dict):
        for k, v in (d or {}).items():
            if isinstance(v, dict):
                setattr(self, k, DotDict(v))
            elif isinstance(v, list):
                setattr(self, k, [DotDict(i) if isinstance(i, dict) else i for i in v])
            else:
                setattr(self, k, v)
    def get(self, key, default=None): return getattr(self, key, default)
    def __getitem__(self, key):       return getattr(self, key)
    def __contains__(self, key):      return hasattr(self, key)
    def __bool__(self):               return True


def render_html(market_data, analysis, dca_result, s2_result, gex_report) -> str:
    env      = Environment(loader=FileSystemLoader("."), autoescape=True)
    template = env.get_template("template.html")

    market_s2 = market_data.get("s2", {})
    s2_combined = {
        "qqq":           market_s2.get("qqq", {}),
        "sphd":          market_s2.get("sphd", {}),
        "qqq_premium":   market_s2.get("qqq_premium", {}),
        "annual_dd":     market_s2.get("annual_dd", {}),
        "dca":           s2_result.get("dca", {}),
        "rebalance":     s2_result.get("rebalance", {}),
        "take_profit":   s2_result.get("take_profit", {}),
        "recovery":      s2_result.get("recovery", {}),
        "checklist":     s2_result.get("checklist", []),
        "monthly_budget": s2_result.get("monthly_budget", 3000),
        "drawdown_pct":  s2_result.get("drawdown_pct"),
        "premium_pct":   s2_result.get("premium_pct"),
        "sphd_div_yield": s2_result.get("sphd_div_yield"),
    }

    # 展平 gex_report，方便模板使用
    gex = gex_report if isinstance(gex_report, dict) else {}

    return template.render(
        date         = market_data.get("date", ""),
        quotes       = [DotDict(q) for q in market_data.get("quotes", [])],
        fear_greed   = DotDict(market_data.get("fear_greed", {})),
        vix          = DotDict(market_data.get("vix", {})),
        qqq_drawdown = market_data.get("qqq_drawdown"),
        analysis     = DotDict(analysis) if isinstance(analysis, dict) else analysis,
        dca          = DotDict(dca_result),
        s2           = DotDict(s2_combined),
        gex          = DotDict(gex),
    )


def send(market_data, analysis, dca_result, s2_result, gex_report=None) -> bool:
    if gex_report is None:
        gex_report = {}
    today   = datetime.datetime.now().strftime("%m/%d")
    pe_str  = _qqq_pe(market_data)
    dca_pct = f"{dca_result.get('total_ratio', 1.0)*100:.0f}%"

    gex_zone = ""
    if gex_report.get("available"):
        gex_zone = f" | {gex_report.get('analysis',{}).get('icon','')} {gex_report.get('analysis',{}).get('zone','')}"

    subject = f"📈 美股简报 {today} | QQQ PE {pe_str} | 定投 {dca_pct}{gex_zone}"

    html_body = render_html(market_data, analysis, dca_result, s2_result, gex_report)
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = EMAIL_SENDER
    msg["To"]      = EMAIL_RECEIVER
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ctx) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
        print(f"✅ 邮件已发送至 {EMAIL_RECEIVER}")
        return True
    except Exception as e:
        print(f"❌ 邮件发送失败：{e}")
        return False


def _qqq_pe(market_data) -> str:
    qqq = next((q for q in market_data.get("quotes",[]) if q.get("symbol")=="QQQ"), {})
    pe  = qqq.get("pe_ratio")
    return f"{pe:.1f}" if pe else "N/A"
