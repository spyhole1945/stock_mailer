"""
strategy2_engine.py
策略二：QQQ + SPHD 双仓联动执行清单计算引擎

三个核心决策：
1. 本月该投多少？（根据 QQQ 折溢价）
2. 需要跨仓调仓吗？（根据年度高点跌幅）
3. 需要止盈吗？（根据估值分位）
"""
from config import (
    S2_MONTHLY_BUDGET, S2_QQQ_INIT, S2_SPHD_INIT,
    S2_PREMIUM_RULES, S2_REBALANCE_RULES, S2_SPHD_MIN,
    S2_TAKE_PROFIT_PE,
)


# ── 第一步：月度定投决策 ─────────────────────────────────

def get_dca_action(premium_pct) -> dict:
    """
    根据 QQQ 折溢价决定本月定投金额
    premium_pct: 溢价百分比（正=溢价，负=折价），None=无法获取
    """
    # 无法获取溢价数据时，默认按正常全额定投处理
    if premium_pct is None:
        return {
            "ratio":   1.0,
            "amount":  S2_MONTHLY_BUDGET,
            "rule":    "溢价数据不可用，按正常全额定投",
            "action":  "FULL",
        }

    for (lower, upper, ratio, desc) in S2_PREMIUM_RULES:
        lower_ok = (lower is None) or (premium_pct >= lower)
        upper_ok = (upper is None) or (premium_pct < upper)
        if lower_ok and upper_ok:
            return {
                "ratio":   ratio,
                "amount":  round(S2_MONTHLY_BUDGET * ratio),
                "rule":    desc,
                "action":  "FULL" if ratio == 1.0 else ("HALF" if ratio == 0.5 else "PAUSE"),
                "premium": premium_pct,
            }

    return {"ratio": 1.0, "amount": S2_MONTHLY_BUDGET, "rule": "正常全额定投", "action": "FULL"}


# ── 第二步：跨仓调仓决策 ─────────────────────────────────

def get_rebalance_action(drawdown_pct) -> dict:
    """
    根据 QQQ 相对年度高点跌幅，决定是否从 SPHD 划转至 QQQ
    drawdown_pct: 负数，如 -15.2 表示跌了15.2%
    """
    if drawdown_pct is None or drawdown_pct >= 0:
        return {
            "triggered":      False,
            "transfer_ratio": 0,
            "desc":           "未触发（当前处于年度高点附近，无需补仓）",
            "action":         "HOLD",
        }

    # 找到触发的最高档位
    triggered_rule = None
    for (threshold, transfer_ratio, desc) in S2_REBALANCE_RULES:
        if drawdown_pct <= threshold:
            triggered_rule = (threshold, transfer_ratio, desc)

    if not triggered_rule:
        return {
            "triggered":      False,
            "transfer_ratio": 0,
            "desc":           f"跌幅 {drawdown_pct:.1f}%，未达5%触发线，继续持仓等待",
            "action":         "HOLD",
        }

    threshold, transfer_ratio, desc = triggered_rule

    # 检查是否超过30%上限
    if drawdown_pct <= -30:
        return {
            "triggered":      True,
            "transfer_ratio": 0.80,
            "sphd_remaining": S2_SPHD_MIN,
            "desc":           f"跌幅已达 {drawdown_pct:.1f}%，超过30%上限，停止继续调仓，锁定 SPHD 底仓 20%",
            "action":         "LOCKED",
            "warning":        "⚠️ 已达最大调仓上限，维持当前仓位，等待修复",
        }

    return {
        "triggered":      True,
        "transfer_ratio": transfer_ratio,
        "sphd_remaining": max(S2_SPHD_INIT * (1 - transfer_ratio), S2_SPHD_MIN),
        "desc":           desc,
        "action":         "TRANSFER",
        "drawdown":       drawdown_pct,
    }


# ── 第三步：止盈决策 ─────────────────────────────────────

def get_take_profit_action(pe_ratio) -> dict:
    """
    根据 QQQ PE 判断是否触发止盈
    文档规则：估值处于历史90%分位以上，主动减仓QQQ 10-20%，转入SPHD
    用 PE > 38 作为90%分位的近似判断
    """
    if pe_ratio is None:
        return {"triggered": False, "desc": "PE 数据不可用，暂不判断止盈"}

    if pe_ratio >= S2_TAKE_PROFIT_PE:
        return {
            "triggered": True,
            "pe":        pe_ratio,
            "desc":      f"QQQ PE={pe_ratio:.1f} 已达历史高估区（≥{S2_TAKE_PROFIT_PE}），建议减仓 QQQ 10–20%，资金转入 SPHD 锁定收益",
            "action":    "REDUCE_QQQ",
        }

    remaining = S2_TAKE_PROFIT_PE - pe_ratio
    return {
        "triggered": False,
        "pe":        pe_ratio,
        "desc":      f"PE={pe_ratio:.1f}，距止盈触发线还有 {remaining:.1f} 个 PE 点，继续持有",
        "action":    "HOLD",
    }


# ── 第四步：行情修复判断 ──────────────────────────────────

def get_recovery_status(drawdown_pct) -> dict:
    """
    判断是否需要执行修复回归（QQQ回升至年度高点后转回SPHD）
    """
    if drawdown_pct is None:
        return {"recovering": False, "desc": "数据不可用"}

    if drawdown_pct >= -1.0:   # 接近年度高点（1%以内视为回归）
        return {
            "recovering": True,
            "desc":       "QQQ 已回升至年度高点附近，如曾执行跨仓调仓，现在应逐步将超额 QQQ 仓位转回 SPHD，恢复 5:5 基准配比",
            "action":     "RESTORE",
        }

    return {
        "recovering": False,
        "desc":       f"QQQ 距年度高点仍有 {drawdown_pct:.1f}%，暂不执行修复回归",
        "action":     "WAIT",
    }


# ── 主计算函数 ────────────────────────────────────────────

def calculate(market_data: dict) -> dict:
    """整合四个决策，生成完整的策略二执行清单"""
    s2        = market_data.get("s2", {})
    annual_dd = s2.get("annual_dd", {})
    premium   = s2.get("qqq_premium", {})
    qqq       = s2.get("qqq", {})
    sphd      = s2.get("sphd", {})

    drawdown_pct  = annual_dd.get("drawdown_pct")
    annual_high   = annual_dd.get("annual_high")
    qqq_price     = annual_dd.get("current_price") or qqq.get("price")
    premium_pct   = premium.get("premium")
    pe_ratio      = qqq.get("pe_ratio")
    sphd_price    = sphd.get("price")
    sphd_div      = sphd.get("dividend_yield")

    dca_action      = get_dca_action(premium_pct)
    rebalance_action = get_rebalance_action(drawdown_pct)
    take_profit     = get_take_profit_action(pe_ratio)
    recovery        = get_recovery_status(drawdown_pct)

    # 生成今日操作清单（给用户看的步骤列表）
    checklist = _build_checklist(dca_action, rebalance_action, take_profit, recovery)

    return {
        "qqq_price":     qqq_price,
        "qqq_pe":        pe_ratio,
        "annual_high":   annual_high,
        "drawdown_pct":  drawdown_pct,
        "premium_pct":   premium_pct,
        "sphd_price":    sphd_price,
        "sphd_div_yield": round(sphd_div * 100, 2) if sphd_div else None,
        "monthly_budget": S2_MONTHLY_BUDGET,

        "dca":          dca_action,
        "rebalance":    rebalance_action,
        "take_profit":  take_profit,
        "recovery":     recovery,
        "checklist":    checklist,
    }


def _build_checklist(dca, rebalance, take_profit, recovery) -> list:
    """生成人类可读的今日操作清单"""
    items = []

    # 止盈优先检查
    if take_profit["triggered"]:
        items.append({
            "priority": "high",
            "icon":     "🔔",
            "title":    "止盈信号触发",
            "action":   take_profit["desc"],
        })

    # 跨仓调仓
    if rebalance["triggered"]:
        if rebalance["action"] == "LOCKED":
            items.append({
                "priority": "medium",
                "icon":     "🔒",
                "title":    "调仓上限已锁定",
                "action":   rebalance["desc"],
            })
        else:
            items.append({
                "priority": "high",
                "icon":     "🔄",
                "title":    f"执行跨仓补仓（划转 SPHD {rebalance['transfer_ratio']*100:.0f}% → QQQ）",
                "action":   rebalance["desc"] + f"，执行后 SPHD 剩余仓位不低于 {S2_SPHD_MIN*100:.0f}%",
            })
    else:
        items.append({
            "priority": "low",
            "icon":     "✅",
            "title":    "跨仓调仓",
            "action":   rebalance["desc"],
        })

    # 月度定投
    if dca["action"] == "PAUSE":
        items.append({
            "priority": "medium",
            "icon":     "⏸️",
            "title":    "本月定投：暂停",
            "action":   dca["rule"] + "，持仓不动，等待下月重新评估",
        })
    elif dca["action"] == "HALF":
        items.append({
            "priority": "medium",
            "icon":     "📊",
            "title":    f"本月定投：减半执行 ${dca['amount']}",
            "action":   dca["rule"],
        })
    else:
        items.append({
            "priority": "low",
            "icon":     "💰",
            "title":    f"本月定投：全额执行 ${dca['amount']}",
            "action":   dca["rule"] + "，按计划买入 QQQ",
        })

    # 修复回归
    if recovery["recovering"]:
        items.append({
            "priority": "medium",
            "icon":     "↩️",
            "title":    "执行修复回归",
            "action":   recovery["desc"],
        })

    return items
