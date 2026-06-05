"""
send_email.py
渲染 HTML 模板并通过 163 SMTP 发送邮件
"""
import smtplib
import ssl
import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Environment, FileSystemLoader
from config import EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECEIVER, SMTP_HOST, SMTP_PORT


def render_html(market_data: dict, analysis: dict) -> str:
    """用 Jinja2 渲染邮件 HTML"""
    env = Environment(loader=FileSystemLoader("."), autoescape=True)
    template = env.get_template("template.html")
    return template.render(
        date          = market_data.get("date", ""),
        quotes        = market_data.get("quotes", []),
        fear_greed    = market_data.get("fear_greed", {}),
        vix           = market_data.get("vix", {}),
        qqq_drawdown  = market_data.get("qqq_drawdown"),
        analysis      = analysis,
    )


def send(market_data: dict, analysis: dict) -> bool:
    """发送邮件，成功返回 True"""
    today = datetime.datetime.now().strftime("%m/%d")
    subject = f"📈 美股简报 {today} | QQQ PE {_qqq_pe(market_data)}"

    html_body = render_html(market_data, analysis)

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


def _qqq_pe(market_data: dict) -> str:
    qqq = next((q for q in market_data.get("quotes", []) if q.get("symbol") == "QQQ"), {})
    pe  = qqq.get("pe_ratio")
    return f"{pe:.1f}" if pe else "N/A"
