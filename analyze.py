"""
analyze.py — DeepSeek AI 分析
"""
import json
import openai
from config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL, POSITION_RULES


def get_position_suggestion(pe_ratio) -> dict:
    if pe_ratio is None:
        return {"position_pct": 60, "level": "未知", "desc": "PE 数据缺失，建议标准仓位"}
    for (pe_min, pe_max), (pct, level, desc) in POSITION_RULES.items():
        if pe_min <= pe_ratio < pe_max:
            return {"position_pct": pct, "level": level, "desc": desc}
    return {"position_pct": 50, "level": "未知", "desc": "PE 超出预设范围"}


def build_prompt(market_data: dict, dca_result: dict,
                 s2_result: dict, gex_report: dict) -> str:
    quotes_text = ""
    for q in market_data.get("quotes", []):
        if "error" in q:
            quotes_text += f"- {q['symbol']}: 数据获取失败\n"
            continue
        pe_str  = f"PE={q['pe_ratio']:.1f}" if q.get("pe_ratio") else "PE=N/A"
        chg_str = f"{q['change_pct']:+.2f}%" if q.get("change_pct") is not None else "N/A"
        quotes_text += (f"- {q['symbol']} ({q.get('name','')}):"
                        f" ${q.get('price','N/A')} {chg_str}  {pe_str}\n")

    fg     = market_data.get("fear_greed", {})
    vix    = market_data.get("vix", {})
    dd     = market_data.get("qqq_drawdown")
    dd_str = f"{dd:+.2f}%" if dd else "N/A"

    dca_summary = "\n".join(dca_result.get("action_summary", []))
    dca_total   = f"{dca_result.get('total_ratio', 1.0)*100:.0f}%"

    s2_dd  = s2_result.get("drawdown_pct")
    s2_checklist = "\n".join(
        f"- [{i['icon']}] {i['title']}：{i['action']}"
        for i in s2_result.get("checklist", [])
    )

    gex_text = ""
    if gex_report.get("available"):
        ga = gex_report.get("analysis", {})
        gex_text = f"""
【期权关键位（Call Wall / Put Wall）】
当前区间：{ga.get('zone','未知')}  {ga.get('icon','')}
Call Wall（压力位）：${gex_report.get('call_wall','N/A')}
Put Wall（支撑位） ：${gex_report.get('put_wall','N/A')}
Gamma Flip        ：${gex_report.get('gamma_flip','N/A')}
Max Pain          ：${gex_report.get('max_pain','N/A')}
操作提示：{ga.get('hint','')}
"""

    prompt = f"""你是一位专业的美股投资分析师，请根据以下今日市场数据，给出简洁、实用的分析报告。

【今日数据】
日期：{market_data.get('date', '')}

{quotes_text}
VIX 恐慌指数：{vix.get('price','N/A')} ({f"{vix.get('change_pct',0):+.1f}%" if vix.get('change_pct') is not None else 'N/A'})
CNN 恐贪指数：{fg.get('score','N/A')} / 100（{fg.get('rating','N/A')}）
QQQ 距52周高点回撤：{dd_str}
{gex_text}
【策略一：三层定投引擎结果】
本期建议总投入：月预算 × {dca_total}
{dca_summary}

【策略二：QQQ+SPHD双仓联动结果】
QQQ 年度高点跌幅：{f"{s2_dd:+.2f}%" if s2_dd else "N/A"}
今日执行清单：
{s2_checklist}

请输出以下十个字段（只返回 JSON，不要任何多余文字和代码块标记）：

{{
  "market_summary": "2-3句话，概括今日美股整体状态和主要驱动因素",
  "qqq_analysis": "针对 QQQ 的具体分析，包括估值、趋势判断，2-3句",
  "position_advice": "整体仓位建议，给出明确百分比和理由，2-3句",
  "dca_comment": "结合策略一引擎结果，1-2句解读本期定投是否合理",
  "s2_comment": "结合策略二执行清单，1-2句点评双仓操作是否合理",
  "gex_comment": "结合 Call Wall/Put Wall 数据，1-2句给出当前价格区间的操作提示",
  "risk_watch": "最需要警惕的1-2个风险点，每条单独一行以- 开头",
  "stocks_comment": "对 NVDA、AAPL、META 各一句简评，格式：股票代码：简评内容",
  "tomorrow_focus": "明日重点关注事项1-2条，每条单独一行以- 开头",
  "symbol_risk": {{
    "QQQ":  {{"level": "低/中/高/极高", "reason": "不超过10个字"}},
    "SPY":  {{"level": "低/中/高/极高", "reason": "不超过10个字"}},
    "VOO":  {{"level": "低/中/高/极高", "reason": "不超过10个字"}},
    "NVDA": {{"level": "低/中/高/极高", "reason": "不超过10个字"}},
    "AAPL": {{"level": "低/中/高/极高", "reason": "不超过10个字"}},
    "META": {{"level": "低/中/高/极高", "reason": "不超过10个字"}}
  }}
}}

要求：语言简洁专业，数据结合上面的具体数字，不要凭空捏造。"""
    return prompt


def analyze(market_data: dict, dca_result: dict,
            s2_result: dict = None, gex_report: dict = None) -> dict:
    if s2_result  is None: s2_result  = {}
    if gex_report is None: gex_report = {}

    qqq = next((q for q in market_data.get("quotes", []) if q["symbol"] == "QQQ"), {})
    rule_suggestion = get_position_suggestion(qqq.get("pe_ratio"))

    if not DEEPSEEK_API_KEY:
        return {"ai_available": False, "rule_suggestion": rule_suggestion,
                "market_summary": "（未配置 DeepSeek API Key，跳过 AI 分析）"}

    try:
        client = openai.OpenAI(api_key=DEEPSEEK_API_KEY,
                               base_url="https://api.deepseek.com")
        prompt = build_prompt(market_data, dca_result, s2_result, gex_report)

        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL, max_tokens=1600,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.choices[0].message.content.strip()
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()

        result = json.loads(raw)
        result["ai_available"]    = True
        result["rule_suggestion"] = rule_suggestion
        return result

    except Exception as e:
        return {"ai_available": False, "rule_suggestion": rule_suggestion,
                "market_summary": f"AI 分析失败：{e}"}
