"""
LLM 润色层：将结构化命理数据交给通义千问，生成自然语言运势解读。
复用 contract-h5 的 OpenAI SDK + DashScope 模式。
"""
import json
import logging
from functools import lru_cache
from typing import Any, Dict, Optional

from .config import get_settings

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

logger = logging.getLogger("fortune.llm")

DEFAULT_READING = {
    "overview": "",
    "career": "",
    "wealth": "",
    "love": "",
    "health": "",
    "tips": "",
}

DEFAULT_YEARLY_READING = {
    "yearly_overview": "",
    "yearly_career": "",
    "yearly_wealth": "",
    "yearly_love": "",
    "yearly_health": "",
    "yearly_advice": "",
    "monthly_highlights": "",
}


@lru_cache(maxsize=1)
def _client() -> Optional[Any]:
    if not HAS_OPENAI:
        return None
    cfg = get_settings()
    if not cfg.api_key:
        return None
    return OpenAI(api_key=cfg.api_key, base_url=cfg.base_url or None)


def generate_reading(
    bazi: Dict,
    wuxing: Dict,
    daily: Dict,
    gender: str,
) -> Dict:
    """
    调用 LLM 生成运势解读文案。

    参数为各模块的计算结果字典。
    返回 {"overview", "career", "wealth", "love", "health", "tips"}。
    """
    client = _client()
    if not client:
        logger.warning("LLM 客户端不可用，返回基于规则的默认解读")
        return _rule_based_reading(bazi, wuxing, daily, gender)

    prompt = _build_prompt(bazi, wuxing, daily, gender)
    cfg = get_settings()

    try:
        logger.info("[LLM] 调用模型: %s", cfg.LLM_MODEL)
        resp = client.chat.completions.create(
            model=cfg.LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=cfg.LLM_MAX_TOKENS,
            temperature=cfg.LLM_TEMPERATURE,
            timeout=cfg.LLM_TIMEOUT,
        )
        content = ""
        if resp.choices:
            msg = resp.choices[0].message
            if msg:
                content = msg.content or ""

        logger.info("[LLM] 返回 %d 字", len(content))
        if not content:
            return _rule_based_reading(bazi, wuxing, daily, gender)

        parsed = _parse_json(content)
        if parsed:
            return _normalize(parsed)

        logger.warning("[LLM] JSON 解析失败，使用规则兜底")
        return _rule_based_reading(bazi, wuxing, daily, gender)

    except Exception as e:
        logger.error("[LLM] 调用异常: %s: %s", type(e).__name__, e)
        return _rule_based_reading(bazi, wuxing, daily, gender)


def _build_prompt(bazi: Dict, wuxing: Dict, daily: Dict, gender: str) -> str:
    pillars = bazi.get('pillars', {})
    bazi_str = " ".join(
        f"{pillars[k]['gan']}{pillars[k]['zhi']}"
        for k in ('year', 'month', 'day', 'hour')
        if k in pillars
    )

    scores = daily.get('scores', {})
    almanac = daily.get('almanac', {})
    lucky = daily.get('lucky', {})

    gender_cn = '男' if gender == 'male' else '女'

    return (
        f"你是一位资深命理师，说话专业又亲切。请根据以下八字排盘数据，"
        f"用专业但通俗易懂的语言撰写今日运势解读。\n\n"
        f"【命主信息】\n"
        f"性别：{gender_cn}\n"
        f"八字：{bazi_str}\n"
        f"日主：{wuxing.get('day_master', '')}\n"
        f"日主旺衰：{wuxing.get('strength', '')}\n"
        f"喜用神：{'、'.join(wuxing.get('favorable', []))}\n"
        f"忌神：{'、'.join(wuxing.get('unfavorable', []))}\n\n"
        f"【今日流日】\n"
        f"日期：{daily.get('date', '')}（{daily.get('lunar_date', '')}）\n"
        f"流日干支：{daily.get('ganzhi', '')}\n\n"
        f"【运势评分】\n"
        f"综合：{scores.get('overall', 70)} "
        f"事业：{scores.get('career', 70)} "
        f"财运：{scores.get('wealth', 70)} "
        f"感情：{scores.get('love', 70)} "
        f"健康：{scores.get('health', 70)}\n\n"
        f"【黄历】\n"
        f"宜：{'、'.join(almanac.get('yi', []))}\n"
        f"忌：{'、'.join(almanac.get('ji', []))}\n\n"
        f"【幸运提示】\n"
        f"幸运色：{lucky.get('color', '')} 幸运数字：{lucky.get('number', '')} "
        f"幸运方位：{lucky.get('direction', '')}\n\n"
        f"请严格输出紧凑 JSON（不换行不缩进），格式如下：\n"
        f'{{"overview":"今日综合运势总评(80字内)",'
        f'"career":"事业运建议(50字内)",'
        f'"wealth":"财运建议(50字内)",'
        f'"love":"感情运建议(50字内)",'
        f'"health":"健康建议(50字内)",'
        f'"tips":"今日小贴士/温馨提醒(60字内)"}}\n\n'
        f"要求：\n"
        f"1. 语气像朋友聊天，专业又温暖，避免生硬\n"
        f"2. 结合八字五行和当日流日分析，给出有针对性的建议\n"
        f"3. overview 要提到具体的五行分析\n"
        f"4. 每项建议都要有可操作性"
    )


def generate_yearly_reading(
    bazi: Dict,
    wuxing: Dict,
    yearly: Dict,
    gender: str,
) -> Dict:
    """
    调用 LLM 生成年度运势解读文案。
    返回 {"yearly_overview", "yearly_career", "yearly_wealth",
           "yearly_love", "yearly_health", "yearly_advice", "monthly_highlights"}。
    """
    client = _client()
    if not client:
        logger.warning("LLM 客户端不可用，返回基于规则的年度默认解读")
        return _rule_based_yearly_reading(bazi, wuxing, yearly, gender)

    prompt = _build_yearly_prompt(bazi, wuxing, yearly, gender)
    cfg = get_settings()

    try:
        logger.info("[LLM] 年度运势调用模型: %s", cfg.LLM_MODEL)
        resp = client.chat.completions.create(
            model=cfg.LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=cfg.LLM_MAX_TOKENS,
            temperature=cfg.LLM_TEMPERATURE,
            timeout=cfg.LLM_TIMEOUT,
        )
        content = ""
        if resp.choices:
            msg = resp.choices[0].message
            if msg:
                content = msg.content or ""

        logger.info("[LLM] 年度运势返回 %d 字", len(content))
        if not content:
            return _rule_based_yearly_reading(bazi, wuxing, yearly, gender)

        parsed = _parse_json(content)
        if parsed:
            return _normalize_yearly(parsed)

        logger.warning("[LLM] 年度 JSON 解析失败，使用规则兜底")
        return _rule_based_yearly_reading(bazi, wuxing, yearly, gender)

    except Exception as e:
        logger.error("[LLM] 年度运势调用异常: %s: %s", type(e).__name__, e)
        return _rule_based_yearly_reading(bazi, wuxing, yearly, gender)


def _build_yearly_prompt(bazi: Dict, wuxing: Dict, yearly: Dict, gender: str) -> str:
    pillars = bazi.get('pillars', {})
    bazi_str = " ".join(
        f"{pillars[k]['gan']}{pillars[k]['zhi']}"
        for k in ('year', 'month', 'day', 'hour')
        if k in pillars
    )

    scores = yearly.get('scores', {})
    taisui = yearly.get('taisui', {})
    monthly = yearly.get('monthly', [])

    gender_cn = '男' if gender == 'male' else '女'

    taisui_str = '无'
    if taisui.get('has_conflict'):
        taisui_str = '、'.join(t['type'] for t in taisui.get('types', []))

    top3 = sorted(monthly, key=lambda m: m.get('score', 0), reverse=True)[:3]
    bot3 = sorted(monthly, key=lambda m: m.get('score', 0))[:3]
    top_str = '、'.join(f"{m['name']}({m['score']}分)" for m in top3)
    bot_str = '、'.join(f"{m['name']}({m['score']}分)" for m in bot3)

    return (
        f"你是一位资深命理师，说话专业又亲切。请根据以下八字排盘数据，"
        f"用专业但通俗易懂的语言撰写本年度运势解读。\n\n"
        f"【命主信息】\n"
        f"性别：{gender_cn}\n"
        f"八字：{bazi_str}\n"
        f"日主：{wuxing.get('day_master', '')}\n"
        f"日主旺衰：{wuxing.get('strength', '')}\n"
        f"喜用神：{'、'.join(wuxing.get('favorable', []))}\n"
        f"忌神：{'、'.join(wuxing.get('unfavorable', []))}\n\n"
        f"【流年信息】\n"
        f"流年：{yearly.get('year', '')} {yearly.get('ganzhi', '')}年"
        f"（{yearly.get('shengxiao', '')}年）\n"
        f"纳音：{yearly.get('nayin', '')}\n"
        f"流年十神：{yearly.get('shishen', '')}\n"
        f"年度主题：{yearly.get('theme', '')}\n"
        f"犯太岁：{taisui_str}\n\n"
        f"【年度评分】\n"
        f"综合：{scores.get('overall', 65)} "
        f"事业：{scores.get('career', 65)} "
        f"财运：{scores.get('wealth', 65)} "
        f"感情：{scores.get('love', 65)} "
        f"健康：{scores.get('health', 65)}\n\n"
        f"【月运概览】\n"
        f"最佳月份：{top_str}\n"
        f"需注意月份：{bot_str}\n\n"
        f"请严格输出紧凑 JSON（不换行不缩进），格式如下：\n"
        f'{{"yearly_overview":"年度综合运势总评(120字内)",'
        f'"yearly_career":"年度事业运建议(80字内)",'
        f'"yearly_wealth":"年度财运建议(80字内)",'
        f'"yearly_love":"年度感情运建议(80字内)",'
        f'"yearly_health":"年度健康建议(80字内)",'
        f'"yearly_advice":"年度总体建议/开运指南(80字内)",'
        f'"monthly_highlights":"上下半年重点提示(80字内)"}}\n\n'
        f"要求：\n"
        f"1. 语气像朋友聊天，专业又温暖，避免生硬\n"
        f"2. 结合八字五行和流年分析，给出有针对性的建议\n"
        f"3. yearly_overview 要提到流年十神和犯太岁情况（如有）\n"
        f"4. 每项建议都要有可操作性\n"
        f"5. 突出重点月份的注意事项"
    )


def _normalize_yearly(raw: Dict) -> Dict:
    out = dict(DEFAULT_YEARLY_READING)
    for key in DEFAULT_YEARLY_READING:
        if isinstance(raw.get(key), str):
            out[key] = raw[key]
    return out


def _rule_based_yearly_reading(bazi: Dict, wuxing: Dict, yearly: Dict, gender: str) -> Dict:
    """无 LLM 时的年度规则兜底文案"""
    dm = wuxing.get('day_master', '日主')
    strength = wuxing.get('strength', '中和')
    favorable = wuxing.get('favorable', [])
    fav_str = '、'.join(favorable) if favorable else '平衡'
    scores = yearly.get('scores', {})
    overall = scores.get('overall', 65)
    gz = yearly.get('ganzhi', '甲子')
    theme = yearly.get('theme', '平稳过渡')
    shishen = yearly.get('shishen', '')
    taisui = yearly.get('taisui', {})

    if overall >= 80:
        mood = "运势大好"
    elif overall >= 65:
        mood = "运势平稳"
    else:
        mood = "运势偏低"

    taisui_text = ""
    if taisui.get('has_conflict'):
        types = '、'.join(t['type'] for t in taisui.get('types', []))
        taisui_text = f"今年{types}，需多加谨慎。"

    monthly = yearly.get('monthly', [])
    top = sorted(monthly, key=lambda m: m.get('score', 0), reverse=True)[:2]
    bot = sorted(monthly, key=lambda m: m.get('score', 0))[:2]
    top_names = '、'.join(m['name'] for m in top) if top else '上半年'
    bot_names = '、'.join(m['name'] for m in bot) if bot else '下半年'

    return {
        'yearly_overview': (
            f"{gz}年整体{mood}，流年十神{shishen}主导「{theme}」之势。"
            f"{dm}{strength}，喜{fav_str}。{taisui_text}"
            f"综合评分{overall}分。"
        ),
        'yearly_career': (
            f"事业评分{scores.get('career', 65)}分，"
            f"{'适合拓展新业务、争取晋升' if scores.get('career', 65) >= 70 else '建议稳扎稳打、蓄积实力'}。"
        ),
        'yearly_wealth': (
            f"财运评分{scores.get('wealth', 65)}分，"
            f"{'可适当把握投资机会' if scores.get('wealth', 65) >= 70 else '不宜冲动消费、大额投资'}。"
        ),
        'yearly_love': (
            f"感情评分{scores.get('love', 65)}分，"
            f"{'桃花运不错，适合发展新关系' if scores.get('love', 65) >= 70 else '与伴侣多沟通，单身者不急'}。"
        ),
        'yearly_health': (
            f"健康评分{scores.get('health', 65)}分，"
            f"{'身体状态良好，保持运动' if scores.get('health', 65) >= 70 else '注意休息和定期体检'}。"
        ),
        'yearly_advice': (
            f"年度关键词「{theme}」，最佳行动期在{top_names}，"
            f"{bot_names}宜低调守成。"
        ),
        'monthly_highlights': (
            f"上半年重点在{top_names}，运势较旺；"
            f"{bot_names}运势偏弱，需特别注意。"
        ),
    }


def _parse_json(content: str) -> Optional[Dict]:
    """三级 JSON 解析容错"""
    content = content.strip()
    for prefix in ("```json", "```"):
        if content.startswith(prefix):
            content = content[len(prefix):].lstrip()
    if content.endswith("```"):
        content = content[:-3].rstrip()

    start = content.find("{")
    if start == -1:
        return None
    fragment = content[start:]

    try:
        return json.loads(fragment)
    except json.JSONDecodeError:
        pass

    # 栈修复截断
    stack = []
    in_str = False
    escape = False
    for ch in fragment:
        if escape:
            escape = False
            continue
        if ch == '\\':
            escape = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if ch in ('{', '['):
            stack.append('}' if ch == '{' else ']')
        elif ch in ('}', ']'):
            if stack and stack[-1] == ch:
                stack.pop()

    fixed = fragment
    if in_str:
        fixed += '"'
    fixed += ''.join(reversed(stack))
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # 逆序截断
    for i in range(len(fragment) - 1, 0, -1):
        if fragment[i] == '}':
            try:
                return json.loads(fragment[:i + 1])
            except json.JSONDecodeError:
                continue
    return None


def _normalize(raw: Dict) -> Dict:
    out = dict(DEFAULT_READING)
    for key in DEFAULT_READING:
        if isinstance(raw.get(key), str):
            out[key] = raw[key]
    return out


def _rule_based_reading(bazi: Dict, wuxing: Dict, daily: Dict, gender: str) -> Dict:
    """无 LLM 时的规则兜底文案"""
    dm = wuxing.get('day_master', '日主')
    strength = wuxing.get('strength', '中和')
    favorable = wuxing.get('favorable', [])
    fav_str = '、'.join(favorable) if favorable else '平衡'
    scores = daily.get('scores', {})
    overall = scores.get('overall', 70)
    gz = daily.get('ganzhi', '甲子')

    if overall >= 80:
        mood = "运势上佳"
    elif overall >= 60:
        mood = "运势平稳"
    else:
        mood = "运势偏低"

    return {
        'overview': f"今日{mood}。{dm}{strength}，喜{fav_str}，流日{gz}对命局整体{'有利' if overall >= 65 else '略有冲击'}，综合评分{overall}分。",
        'career': f"事业方面评分{scores.get('career', 70)}分，{'适合推进重要项目' if scores.get('career', 70) >= 70 else '建议稳扎稳打'}。",
        'wealth': f"财运评分{scores.get('wealth', 70)}分，{'可以把握投资机会' if scores.get('wealth', 70) >= 70 else '不宜冲动消费'}。",
        'love': f"感情评分{scores.get('love', 70)}分，{'桃花运不错，多出去走走' if scores.get('love', 70) >= 70 else '与伴侣多沟通理解'}。",
        'health': f"健康评分{scores.get('health', 70)}分，{'身体状态良好' if scores.get('health', 70) >= 70 else '注意休息，避免过度劳累'}。",
        'tips': f"今日幸运色{daily.get('lucky', {}).get('color', '绿色')}，幸运数字{daily.get('lucky', {}).get('number', 3)}，适宜朝{daily.get('lucky', {}).get('direction', '东')}方发展。",
    }
