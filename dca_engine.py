"""
dca_engine.py
三层定投策略计算引擎
根据当前市场数据（PE、回撤、恐贪指数）计算本期各层建议投入金额
"""
from config import (
    DCA_LAYER1_RATIO, DCA_LAYER2_RATIO, DCA_LAYER3_RATIO,
    DCA_LAYER2_PE_MULTIPLIER, DCA_LAYER3_TRIGGERS,
    DCA_TAKE_PROFIT_PE, POSITION_RULES
)


def get_layer2_multiplier(pe_ratio: float) -> tuple:
    """根据 PE 获取第二层投入系数"""
    if pe_ratio is None:
        return 1.0, "PE 未知，按标准投入"
    for (pe_min, pe_max), multiplier in DCA_LAYER2_PE_MULTIPLIER.items():
        if pe_min <= pe_ratio < pe_max:
            if multiplier == 0:
                return 0.0, f"PE={pe_ratio:.1f} 极度高估，暂停第二层"
            elif multiplier > 1:
                return multiplier, f"PE={pe_ratio:.1f} 低估区，超配 {multiplier}x"
            elif multiplier == 1:
                return multiplier, f"PE={pe_ratio:.1f} 合理区，标准投入"
            else:
                return multiplier, f"PE={pe_ratio:.1f} 偏高区，缩减至 {multiplier}x"
    return 1.0, "PE 超出预设范围，标准投入"


def get_layer3_action(drawdown_pct: float) -> tuple:
    """根据回撤幅度判断第三层是否触发"""
    if drawdown_pct is None or drawdown_pct > -15:
        return False, 0.0, "未触发（回撤不足15%）"
    # 取最高档触发
    result_multiplier = 0.0
    result_desc = ""
    for (threshold, multiplier, desc) in DCA_LAYER3_TRIGGERS:
        if drawdown_pct <= threshold:
            result_multiplier = multiplier
            result_desc = desc
    if result_multiplier > 0:
        return True, result_multiplier, result_desc
    return False, 0.0, "未触发"


def get_take_profit_signal(pe_ratio: float) -> dict:
    """判断是否触发止盈信号"""
    if pe_ratio is None:
        return {"triggered": False, "desc": "PE 数据缺失"}
    if pe_ratio >= DCA_TAKE_PROFIT_PE:
        return {
            "triggered": True,
            "desc": f"PE={pe_ratio:.1f} 已超止盈参考线 {DCA_TAKE_PROFIT_PE}，考虑减仓 10–20%，保留底仓"
        }
    remaining = DCA_TAKE_PROFIT_PE - pe_ratio
    return {
        "triggered": False,
        "desc": f"距止盈参考线（PE={DCA_TAKE_PROFIT_PE}）还有 {remaining:.1f} 个 PE 点"
    }


def calculate(market_data: dict, monthly_budget: float = None) -> dict:
    """
    主计算函数
    monthly_budget: 月度总预算（可选，填入后输出具体金额；不填则只输出比例）
    """
    qqq = next((q for q in market_data.get("quotes", []) if q["symbol"] == "QQQ"), {})
    pe_ratio  = qqq.get("pe_ratio")
    drawdown  = market_data.get("qqq_drawdown")
    fg_score  = market_data.get("fear_greed", {}).get("score")

    # ── 第一层：无条件执行 ──────────────────────────────
    layer1_ratio = DCA_LAYER1_RATIO
    layer1_desc  = "无条件执行，确保持续入场"

    # ── 第二层：PE 估值增强 ─────────────────────────────
    l2_multiplier, l2_reason = get_layer2_multiplier(pe_ratio)
    layer2_ratio  = DCA_LAYER2_RATIO * l2_multiplier
    layer2_active = l2_multiplier > 0

    # ── 第三层：极端机会 ────────────────────────────────
    l3_triggered, l3_multiplier, l3_reason = get_layer3_action(drawdown)
    layer3_ratio  = DCA_LAYER3_RATIO * l3_multiplier if l3_triggered else 0.0

    # ── 恐贪指数修正（情绪过滤）───────────────────────
    emotion_note = ""
    emotion_multiplier = 1.0
    if fg_score is not None:
        if fg_score >= 80:
            emotion_multiplier = 0.7
            emotion_note = f"⚠️ 恐贪指数 {fg_score}（极度贪婪），整体缩减至 70%"
        elif fg_score >= 65:
            emotion_multiplier = 0.85
            emotion_note = f"恐贪指数 {fg_score}（贪婪），略微缩减"
        elif fg_score <= 20:
            emotion_multiplier = 1.2
            emotion_note = f"✅ 恐贪指数 {fg_score}（极度恐惧），市场恐慌是机会，适度加码"
        elif fg_score <= 35:
            emotion_multiplier = 1.1
            emotion_note = f"恐贪指数 {fg_score}（恐惧），略微加码"

    # ── 本期总投入比例 ──────────────────────────────────
    total_ratio_before_emotion = layer1_ratio + layer2_ratio + layer3_ratio
    total_ratio = min(total_ratio_before_emotion * emotion_multiplier, 2.0)  # 最多双倍预算

    # ── 止盈信号 ────────────────────────────────────────
    take_profit = get_take_profit_signal(pe_ratio)

    # ── 构建结果 ────────────────────────────────────────
    result = {
        "pe_ratio":   pe_ratio,
        "drawdown":   drawdown,
        "fg_score":   fg_score,

        "layer1": {
            "ratio":  layer1_ratio,
            "desc":   layer1_desc,
            "active": True,
        },
        "layer2": {
            "ratio":       layer2_ratio,
            "multiplier":  l2_multiplier,
            "reason":      l2_reason,
            "active":      layer2_active,
        },
        "layer3": {
            "ratio":       layer3_ratio,
            "triggered":   l3_triggered,
            "multiplier":  l3_multiplier,
            "reason":      l3_reason,
        },

        "emotion_multiplier": emotion_multiplier,
        "emotion_note":       emotion_note,
        "total_ratio":        round(total_ratio, 3),
        "take_profit":        take_profit,

        # 人类可读的本期操作建议
        "action_summary": _build_action_summary(
            layer1_ratio, layer2_ratio, layer2_active, l2_reason,
            l3_triggered, layer3_ratio, l3_reason,
            emotion_note, total_ratio, take_profit
        ),
    }

    # 如果提供了月预算，额外计算具体金额
    if monthly_budget:
        result["monthly_budget"] = monthly_budget
        result["layer1_amount"]  = round(monthly_budget * layer1_ratio, 2)
        result["layer2_amount"]  = round(monthly_budget * layer2_ratio, 2)
        result["layer3_amount"]  = round(monthly_budget * layer3_ratio, 2)
        result["total_amount"]   = round(monthly_budget * total_ratio, 2)

    return result


def _build_action_summary(
    l1r, l2r, l2_active, l2_reason,
    l3_triggered, l3r, l3_reason,
    emotion_note, total_ratio, take_profit
) -> list:
    """生成人类可读的操作步骤列表"""
    steps = []

    steps.append(f"✅ 第一层（基础定投）：执行月预算 {l1r*100:.0f}%，本月固定买入")

    if l2_active:
        steps.append(f"📊 第二层（估值增强）：{l2_reason}，投入月预算 {l2r*100:.0f}%")
    else:
        steps.append(f"⏸️ 第二层（估值增强）：{l2_reason}，本月暂停")

    if l3_triggered:
        steps.append(f"🚨 第三层（极端机会）：{l3_reason}，追加月预算 {l3r*100:.0f}%")
    else:
        steps.append(f"💤 第三层（极端机会）：{l3_reason}，子弹保留待命")

    if emotion_note:
        steps.append(f"🎭 情绪修正：{emotion_note}")

    steps.append(f"📌 本期合计：月预算 × {total_ratio*100:.0f}%")

    if take_profit["triggered"]:
        steps.append(f"🔔 止盈提示：{take_profit['desc']}")

    return steps
