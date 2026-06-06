"""
analyze.py
把采集到的数据发给 DeepSeek API，获取仓位建议和市场解读
"""
import json
import openai
from config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL, POSITION_RULES


def get_position_suggestion(pe_ratio) -> dict:
    """根据 QQQ PE 给出规则引擎仓位建议（不依赖 AI，作为兜底）"""
    if pe_ratio is None:
        return {"position_pct": 60, "level": "未知", "desc": "PE 数据缺失，建议标准仓位"}
    for (pe_min, pe_max), (pct, level, desc) in POSITION_RULES.items():
        if pe_min <= pe_ratio < pe_max:
            return {"position_pct": pct, "level": level, "desc": desc}
    return {"position_pct": 50, "level": "未知", "desc": "PE 超出预设范围"}


def build_prompt(market_data: dict) -> str:
    """构建发给 DeepSeek 的 prompt"""
    quotes_text = ""
    for q in market_data.get("quotes", []):
        if "error" in q:
            quotes_text += f"- {q['symbol']}: 数据获取失败\n"
            continue
        pe_str  = f"PE={q['pe_ratio']:.1f}" if q.get("pe_ratio") else "PE=N/A"
        chg_str = f"{q['change_pct']:+.2f}%" if q.get("change_pct") is not None else "N/A"
        quotes_text += (
            f"- {q['symbol']} ({q.get('name','')}): "
            f"${q.get('price','N/A')} {chg_str}  {pe_str}\n"
        )

    fg     = market_data.get("fear_greed", {})
    vix    = market_data.get("vix", {})
    dd     = market_data.get("qqq_drawdown")
    dd_str = f"{dd:+.2f}%" if dd else "N/A"

    prompt = f"""你是一位专业的美股投资分析师，请根据以下今日市场数据，给出简洁、实用的分析报告。

【今日数据】
日期：{market_data.get('date', '')}

{quotes_text}
VIX 恐慌指数：{vix.get('price', 'N/A')} ({f"{vix.get('change_pct',0):+.1f}%" if vix.get('change_pct') is not None else 'N/A'})
CNN 恐贪指数：{fg.get('score', 'N/A')} / 100 （{fg.get('rating', 'N/A')}）
QQQ 距52周高点回撤：{dd_str}

请输出以下六个字段（只返回 JSON，不要任何多余文字和代码块标记）：

{{
  "market_summary": "2-3句话，概括今日美股整体状态和主要驱动因素",
  "qqq_analysis": "针对 QQQ 的具体分析，包括估值、趋势判断，2-3句",
  "position_advice": "仓位建议，说明当前应持有多少比例的权益资产（如 QQQ/SPY），给出明确的百分比和理由，3-4句",
  "risk_watch": "当前最需要警惕的1-2个风险点，每个风险点单独一行，以- 开头",
  "stocks_comment": "对 NVDA、AAPL、MSFT 各一句简评，每行格式为：股票代码：简评内容",
  "tomorrow_focus": "明日重点关注事项，1-2条，每条单独一行，以- 开头"
}}

要求：语言简洁专业，避免废话，数据要结合上面提供的具体数字，不要凭空捏造。"""
    return prompt


def analyze(market_data: dict) -> dict:
    """调用 DeepSeek API 进行分析，返回结构化结果"""
    # 先用规则引擎算仓位（兜底）
    qqq = next((q for q in market_data.get("quotes", []) if q["symbol"] == "QQQ"), {})
    rule_suggestion = get_position_suggestion(qqq.get("pe_ratio"))

    if not DEEPSEEK_API_KEY:
        return {
            "ai_available":  False,
            "rule_suggestion": rule_suggestion,
            "market_summary": "（未配置 DeepSeek API Key，跳过 AI 分析）",
        }

    try:
        client = openai.OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com",
        )
        prompt = build_prompt(market_data)

        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.choices[0].message.content.strip()

        # 清理可能的 markdown 代码块标记
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()

        result = json.loads(raw)
        result["ai_available"]    = True
        result["rule_suggestion"] = rule_suggestion
        return result

    except Exception as e:
        return {
            "ai_available":    False,
            "rule_suggestion": rule_suggestion,
            "market_summary":  f"AI 分析失败：{e}",
        }
