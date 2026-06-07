"""
fetch_data.py
采集所有标的的行情数据 + 市场情绪指数 + 策略二专用数据
"""
import json
import datetime
import requests
import yfinance as yf
from config import ALL_SYMBOLS, ETF_SYMBOLS, S2_SYMBOLS


def _pct(val):
    """格式化百分比"""
    return f"{val:+.2f}%" if val is not None else "N/A"


def fetch_quote(symbol: str) -> dict:
    """获取单只股票/ETF的关键数据"""
    try:
        ticker = yf.Ticker(symbol)
        info   = ticker.info
        hist   = ticker.history(period="2d")

        price      = info.get("regularMarketPrice") or info.get("currentPrice") or (hist["Close"].iloc[-1] if len(hist) else None)
        prev_close = info.get("regularMarketPreviousClose") or (hist["Close"].iloc[-2] if len(hist) >= 2 else None)
        change_pct = ((price - prev_close) / prev_close * 100) if price and prev_close else None

        return {
            "symbol":       symbol,
            "price":        round(price, 2)      if price      else None,
            "change_pct":   round(change_pct, 2) if change_pct else None,
            "pe_ratio":     info.get("trailingPE") or info.get("forwardPE"),
            "pb_ratio":     info.get("priceToBook"),
            "volume":       info.get("regularMarketVolume"),
            "avg_volume":   info.get("averageVolume"),
            "week52_high":  info.get("fiftyTwoWeekHigh"),
            "week52_low":   info.get("fiftyTwoWeekLow"),
            "market_cap":   info.get("marketCap"),
            "name":         info.get("shortName", symbol),
            "dividend_yield": info.get("dividendYield"),
        }
    except Exception as e:
        return {"symbol": symbol, "error": str(e)}


def fetch_qqq_premium() -> dict:
    """
    估算 QQQ 折溢价（用 QQQ 价格 vs NAV 估算）
    yfinance 无法直接获取实时 NAV，用 QQQ 与 QLD（2x）的比值做近似估算
    实际折溢价很小（通常 <0.1%），此处返回近似值供参考
    """
    try:
        ticker = yf.Ticker("QQQ")
        info   = ticker.info
        # Yahoo Finance 有时会提供 navPrice
        nav    = info.get("navPrice")
        price  = info.get("regularMarketPrice") or info.get("currentPrice")
        if nav and price:
            premium = (price - nav) / nav * 100
            return {
                "price":   round(price, 2),
                "nav":     round(nav, 2),
                "premium": round(premium, 2),
                "source":  "yahoo_nav",
            }
        # 无法获取 NAV 时返回 None，策略引擎按溢价<3%处理（正常定投）
        return {"price": price, "nav": None, "premium": None, "source": "unavailable"}
    except Exception as e:
        return {"price": None, "nav": None, "premium": None, "source": f"error:{e}"}


def fetch_qqq_annual_drawdown() -> dict:
    """
    计算 QQQ 相对本年度最高点的跌幅（策略二核心指标）
    基准：当年1月1日至今的最高收盘价
    """
    try:
        ticker    = yf.Ticker("QQQ")
        year_start = f"{datetime.date.today().year}-01-01"
        hist      = ticker.history(start=year_start)

        if hist.empty:
            return {"annual_high": None, "current_price": None, "drawdown_pct": None}

        annual_high   = float(hist["Close"].max())
        current_price = float(hist["Close"].iloc[-1])
        drawdown_pct  = (current_price - annual_high) / annual_high * 100

        return {
            "annual_high":   round(annual_high, 2),
            "current_price": round(current_price, 2),
            "drawdown_pct":  round(drawdown_pct, 2),
        }
    except Exception as e:
        return {"annual_high": None, "current_price": None, "drawdown_pct": None, "error": str(e)}


def fetch_fear_greed() -> dict:
    """获取 CNN Fear & Greed Index"""
    try:
        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=10)
        data = resp.json()
        score = data["fear_and_greed"]["score"]
        rating = data["fear_and_greed"]["rating"]
        return {"score": round(score, 1), "rating": rating}
    except Exception:
        return {"score": None, "rating": "N/A"}


def fetch_vix() -> dict:
    """获取 VIX 恐慌指数"""
    try:
        vix  = yf.Ticker("^VIX")
        hist = vix.history(period="2d")
        price    = hist["Close"].iloc[-1]   if len(hist) >= 1 else None
        prev     = hist["Close"].iloc[-2]   if len(hist) >= 2 else None
        chg_pct  = ((price - prev) / prev * 100) if price and prev else None
        return {
            "price":      round(price, 2)    if price    else None,
            "change_pct": round(chg_pct, 2)  if chg_pct  else None,
        }
    except Exception:
        return {"price": None, "change_pct": None}


def fetch_all() -> dict:
    """主入口：采集全部数据"""
    today = datetime.datetime.now().strftime("%Y-%m-%d %A")

    # 策略一标的（行情速览）
    quotes     = [fetch_quote(s) for s in ALL_SYMBOLS]
    fear_greed = fetch_fear_greed()
    vix        = fetch_vix()

    # 策略一：QQQ 距 52 周高点回撤
    qqq_data  = next((q for q in quotes if q["symbol"] == "QQQ"), {})
    qqq_price = qqq_data.get("price")
    qqq_high  = qqq_data.get("week52_high")
    drawdown_52w = ((qqq_price - qqq_high) / qqq_high * 100) if qqq_price and qqq_high else None

    # 策略二专用数据
    s2_quotes        = [fetch_quote(s) for s in S2_SYMBOLS if s not in ALL_SYMBOLS]
    qqq_premium      = fetch_qqq_premium()
    qqq_annual_dd    = fetch_qqq_annual_drawdown()

    # 合并策略二的 QQQ/SPHD 报价（避免重复请求）
    sphd_quote = next((q for q in s2_quotes if q["symbol"] == "SPHD"), fetch_quote("SPHD"))

    return {
        "date":          today,
        "quotes":        quotes,
        "fear_greed":    fear_greed,
        "vix":           vix,
        "qqq_drawdown":  round(drawdown_52w, 2) if drawdown_52w else None,
        # 策略二专用
        "s2": {
            "qqq":         qqq_data,
            "sphd":        sphd_quote,
            "qqq_premium": qqq_premium,
            "annual_dd":   qqq_annual_dd,
        },
    }


if __name__ == "__main__":
    data = fetch_all()
    print(json.dumps(data, indent=2, ensure_ascii=False, default=str))
