"""
main.py
主入口 — GitHub Actions 每天调用这个文件
"""
import sys
from fetch_data import fetch_all
from analyze    import analyze
from send_email import send


def main():
    print("📡 正在采集市场数据...")
    market_data = fetch_all()

    print("🤖 正在 AI 分析...")
    analysis = analyze(market_data)

    print("📧 正在发送邮件...")
    ok = send(market_data, analysis)

    if not ok:
        sys.exit(1)
    print("🎉 完成！")


if __name__ == "__main__":
    main()
