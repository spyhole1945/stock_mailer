"""
gex_engine.py
基于 yfinance 期权链数据，免费计算 QQQ 的：
  - Call Wall（最大 Call OI 行权价 = 压力位）
  - Put Wall （最大 Put  OI 行权价 = 支撑位）
  - Gamma Flip（GEX 从正转负的临界价格）
  - Max Pain  （令期权买方亏损最大的行权价）

完全免费，无需任何第三方 API Key。
"""

import math
import datetime
import yfinance as yf
import pandas as pd

CONTRACT_SIZE   = 100   # 每张期权合约对应 100 股
MAX_EXPIRY_DAYS = 45    # 只采集近 45 天内到期的期权


# ── 数据采集 ──────────────────────────────────────────────

def fetch_options_chain(symbol: str = "QQQ") -> dict:
    """从 yfinance 拉取近期期权链，按行权价聚合 OI"""
    try:
        ticker     = yf.Ticker(symbol)
        spot_price = (ticker.info.get("regularMarketPrice")
                      or ticker.info.get("currentPrice"))
        if not spot_price:
            hist       = ticker.history(period="1d")
            spot_price = float(hist["Close"].iloc[-1]) if not hist.empty else None
        if not spot_price:
            return {"available": False, "reason": "无法获取当前股价"}

        today       = datetime.date.today()
        expirations = ticker.options

        all_calls, all_puts = [], []
        for exp_str in expirations:
            exp_date    = datetime.date.fromisoformat(exp_str)
            days_to_exp = (exp_date - today).days
            if days_to_exp < 0 or days_to_exp > MAX_EXPIRY_DAYS:
                continue
            chain = ticker.option_chain(exp_str)
            calls = chain.calls[["strike", "openInterest", "impliedVolatility"]].copy()
            puts  = chain.puts [["strike", "openInterest", "impliedVolatility"]].copy()
            calls["dte"] = days_to_exp
            puts ["dte"] = days_to_exp
            all_calls.append(calls)
            all_puts.append(puts)

        if not all_calls:
            return {"available": False, "reason": "近期无到期期权数据"}

        calls_df = pd.concat(all_calls).groupby("strike", as_index=False).agg(
            openInterest=("openInterest", "sum"),
            impliedVolatility=("impliedVolatility", "mean"),
            dte=("dte", "min"),
        )
        puts_df = pd.concat(all_puts).groupby("strike", as_index=False).agg(
            openInterest=("openInterest", "sum"),
            impliedVolatility=("impliedVolatility", "mean"),
            dte=("dte", "min"),
        )
        return {"available": True, "spot_price": spot_price,
                "calls": calls_df, "puts": puts_df}

    except Exception as e:
        return {"available": False, "reason": f"期权数据采集失败：{e}"}


# ── 核心计算 ──────────────────────────────────────────────

def calc_walls(calls_df, puts_df) -> dict:
    """Call Wall = 最大 Call OI；Put Wall = 最大 Put OI"""
    cw = calls_df.loc[calls_df["openInterest"].idxmax()]
    pw = puts_df.loc[puts_df["openInterest"].idxmax()]
    return {
        "call_wall":    float(cw["strike"]),
        "call_wall_oi": int(cw["openInterest"]),
        "put_wall":     float(pw["strike"]),
        "put_wall_oi":  int(pw["openInterest"]),
    }


def calc_gamma_flip(calls_df, puts_df, spot) -> float | None:
    """简化 GEX 模型，找到 net GEX 从正转负的临界行权价"""
    try:
        merged = pd.merge(
            calls_df[["strike","openInterest","impliedVolatility"]].rename(
                columns={"openInterest":"call_oi","impliedVolatility":"call_iv"}),
            puts_df [["strike","openInterest","impliedVolatility"]].rename(
                columns={"openInterest":"put_oi", "impliedVolatility":"put_iv"}),
            on="strike", how="outer"
        ).fillna(0)
        merged = merged[(merged["strike"] >= spot * 0.8) &
                        (merged["strike"] <= spot * 1.2)].sort_values("strike")

        def gamma_approx(S, K, iv, dte=30):
            if iv <= 0 or dte <= 0:
                return 0
            T   = dte / 365
            sig = iv * math.sqrt(T)
            if sig == 0:
                return 0
            d1  = (math.log(S / K) + 0.5 * iv**2 * T) / sig
            return math.exp(-0.5*d1**2) / math.sqrt(2*math.pi) / (S * sig)

        rows = []
        for _, r in merged.iterrows():
            iv  = max(r["call_iv"], r["put_iv"], 0.15)
            g   = gamma_approx(spot, r["strike"], iv)
            gex = (r["call_oi"] - r["put_oi"]) * g * CONTRACT_SIZE * spot**2
            rows.append({"strike": r["strike"], "gex": gex})

        gdf = pd.DataFrame(rows).sort_values("strike")
        gdf["cum_gex"] = gdf["gex"].cumsum()
        neg = gdf[gdf["cum_gex"] < 0]
        return float(neg.iloc[0]["strike"]) if not neg.empty else None
    except Exception:
        return None


def calc_max_pain(calls_df, puts_df) -> float | None:
    """Max Pain = 令所有期权买方亏损总额最大的行权价"""
    try:
        strikes = sorted(set(calls_df["strike"]).union(set(puts_df["strike"])))
        call_oi = dict(zip(calls_df["strike"], calls_df["openInterest"]))
        put_oi  = dict(zip(puts_df ["strike"], puts_df ["openInterest"]))
        best_P, best_pain = None, float("inf")
        for P in strikes:
            pain = (sum(call_oi.get(K,0) * max(P-K,0) for K in strikes) +
                    sum(put_oi.get(K, 0) * max(K-P,0) for K in strikes))
            if pain < best_pain:
                best_pain, best_P = pain, P
        return float(best_P) if best_P else None
    except Exception:
        return None


# ── 区间判断与操作提示 ────────────────────────────────────

def analyze_position(spot, call_wall, put_wall, gamma_flip=None) -> dict:
    dist_to_call = (call_wall - spot) / spot * 100
    dist_to_put  = (spot - put_wall)  / spot * 100
    gamma_regime = None
    if gamma_flip:
        gamma_regime = "正Gamma（波动收敛）" if spot > gamma_flip else "负Gamma（波动放大）"

    if spot >= call_wall:
        zone, icon = "突破压力位", "🚀"
        desc = f"已突破 Call Wall ${call_wall:.0f}，做市商对冲卖压消失，趋势偏强"
        hint = "压力突破信号，可维持持仓；若伴随放量则信号更可靠"
    elif spot <= put_wall:
        zone, icon = "跌破支撑位", "⚠️"
        desc = f"已跌破 Put Wall ${put_wall:.0f}，做市商买盘支撑减弱，可能加速下跌"
        hint = "支撑失效，建议观望；第三层子弹介入需分批小额，不宜重仓"
    elif dist_to_call <= 1.5:
        zone, icon = "接近压力位", "🔶"
        desc = f"距 Call Wall ${call_wall:.0f} 仅 {dist_to_call:.1f}%，上方压力较重"
        hint = "上行空间受限，不建议此时追高加仓"
    elif dist_to_put <= 1.5:
        zone, icon = "接近支撑位", "🟢"
        desc = f"距 Put Wall ${put_wall:.0f} 仅 {dist_to_put:.1f}%，下方支撑较强"
        hint = "接近支撑，是相对安全的补仓窗口，可考虑小额提前介入"
    else:
        zone, icon = "区间中性", "⚪"
        desc = f"价格处于 Put Wall ${put_wall:.0f} 与 Call Wall ${call_wall:.0f} 之间"
        hint = "按既定策略正常执行，无需特别调整"

    return {"zone": zone, "icon": icon, "desc": desc, "hint": hint,
            "dist_to_call": round(dist_to_call, 2),
            "dist_to_put":  round(dist_to_put,  2),
            "gamma_regime": gamma_regime}


def get_dca_adjustment(zone: str) -> dict:
    MAP = {
        "接近支撑位": (1.15, "✅ 接近 Put Wall，补仓质量较好，可适度加仓 +15%"),
        "跌破支撑位": (0.70, "⚠️ 跌破 Put Wall，支撑失效，建议减少加仓至 70%，分批观察"),
        "接近压力位": (0.85, "🔶 接近 Call Wall，短期上行受限，买入缩减至 85%"),
        "突破压力位": (1.00, "🚀 突破 Call Wall，趋势偏强，维持原计划"),
        "区间中性":   (1.00, "区间中性，按原策略执行"),
    }
    multiplier, note = MAP.get(zone, (1.00, "数据不可用，按原策略执行"))
    return {"multiplier": multiplier, "note": note}


# ── 主入口 ────────────────────────────────────────────────

def get_gex_report(symbol: str = "QQQ") -> dict:
    """完整 GEX 报告：采集 → 计算 → 分析 → 修正建议"""
    raw = fetch_options_chain(symbol)
    if not raw.get("available"):
        return {
            "available":  False,
            "reason":     raw.get("reason", "数据不可用"),
            "analysis":   {"zone": "未知", "icon": "❓",
                           "desc": raw.get("reason",""), "hint": ""},
            "adjustment": {"multiplier": 1.0, "note": "数据不可用，按原策略执行"},
        }

    spot, calls, puts = raw["spot_price"], raw["calls"], raw["puts"]
    walls      = calc_walls(calls, puts)
    gamma_flip = calc_gamma_flip(calls, puts, spot)
    max_pain   = calc_max_pain(calls, puts)
    analysis   = analyze_position(spot, walls["call_wall"], walls["put_wall"], gamma_flip)
    adjustment = get_dca_adjustment(analysis["zone"])

    return {
        "available":    True,
        "symbol":       symbol,
        "spot_price":   round(spot, 2),
        "call_wall":    walls["call_wall"],
        "call_wall_oi": walls["call_wall_oi"],
        "put_wall":     walls["put_wall"],
        "put_wall_oi":  walls["put_wall_oi"],
        "gamma_flip":   round(gamma_flip, 2) if gamma_flip else None,
        "max_pain":     round(max_pain, 2)   if max_pain   else None,
        "analysis":     analysis,
        "adjustment":   adjustment,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(get_gex_report("QQQ"), indent=2, ensure_ascii=False, default=str))
