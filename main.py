"""
main.py — 主入口
"""
import sys
from fetch_data       import fetch_all
from dca_engine       import calculate as dca_calculate
from strategy2_engine import calculate as s2_calculate
from gex_engine       import get_gex_report
from analyze          import analyze
from send_email       import send


def main():
    print("📡 正在采集市场数据...")
    market_data = fetch_all()

    print("📐 正在计算策略一（三层定投）...")
    dca_result = dca_calculate(market_data)

    print("📐 正在计算策略二（QQQ+SPHD双仓）...")
    s2_result = s2_calculate(market_data)

    print("📐 正在计算 Call Wall / Put Wall...")
    qqq_price = dca_result.get("qqq_price")
    gex_report = get_gex_report("QQQ")

    print("🤖 正在 AI 分析...")
    analysis = analyze(market_data, dca_result, s2_result, gex_report)

    print("📧 正在发送邮件...")
    ok = send(market_data, analysis, dca_result, s2_result, gex_report)

    if not ok:
        sys.exit(1)
    print("🎉 完成！")


if __name__ == "__main__":
    main()
