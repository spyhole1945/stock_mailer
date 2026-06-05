"""
fetch_data.py
采集所有标的的行情数据 + 市场情绪指数
"""
import json
import datetime
import requests
import yfinance as yf
from config import ALL_SYMBOLS, ETF_SYMBOLS


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
        }
    except Exception as e:
        return {"symbol": symbol, "error": str(e)}


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
        # 备用：返回 N/A
        return {"score": None, "rating": "N/A"}


def fetch_vix() -> dict:
    """获取 VIX 恐慌指数"""
    try:
        vix  = yf.Ticker("^VIX")
        info = vix.info
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

    quotes     = [fetch_quote(s) for s in ALL_SYMBOLS]
    fear_greed = fetch_fear_greed()
    vix        = fetch_vix()

    # 计算 QQQ 距 52 周高点的回撤
    qqq_data  = next((q for q in quotes if q["symbol"] == "QQQ"), {})
    qqq_price = qqq_data.get("price")
    qqq_high  = qqq_data.get("week52_high")
    drawdown  = ((qqq_price - qqq_high) / qqq_high * 100) if qqq_price and qqq_high else None

    return {
        "date":        today,
        "quotes":      quotes,
        "fear_greed":  fear_greed,
        "vix":         vix,
        "qqq_drawdown": round(drawdown, 2) if drawdown else None,
    }


if __name__ == "__main__":
    data = fetch_all()
    print(json.dumps(data, indent=2, ensure_ascii=False))
