"""
LLM 认知引擎 — 多专家协作系统 + 流式输出 + 对话式交互

设计哲学（Best Minds 三重视角）：
- Ilya Sutskever: LLM 不执行规则，而是学习命理师的思维模式
- 俞军: 降低用户认知负荷，千年命理智慧变成人人可懂的故事
- 徐乐吾: 每句话都有经典依据，RAG + CoT 确保准确性
"""
import json
import logging
from functools import lru_cache
from typing import Any, Dict, Generator, List, Optional

from .config import get_settings

try:
    from openai import OpenAI
    import httpx
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    httpx = None

logger = logging.getLogger("fortune.llm")

# ── 默认兜底结构 ────────────────────────────────────────

DEFAULT_READING = {
    "overview": "", "career": "", "wealth": "",
    "love": "", "health": "", "tips": "",
}

DEFAULT_YEARLY_READING = {
    "yearly_overview": "", "yearly_career": "", "yearly_wealth": "",
    "yearly_love": "", "yearly_health": "", "yearly_advice": "",
    "monthly_highlights": "",
}

# ── 多专家系统 prompt ───────────────────────────────────

MULTI_EXPERT_SYSTEM = """你是一位融合四大流派的AI命理大师，同时具备以下四位专家的思维模式：

## 格局专家（精通《子平真诠》沈孝瞻体系）
- 核心方法：月令透干定格局，成败高低论吉凶
- 分析路径：先看月令本气→透干定格→查成格条件→论格局高低
- 经典引用：《子平真诠》原文

## 调候专家（精通《穷通宝鉴》余春台体系）
- 核心方法：以月令定寒暖燥湿，取调候用神
- 分析路径：定季节→判寒暖→取调候→验喜忌
- 经典引用：《穷通宝鉴》原文

## 象法专家（精通盲派实战体系）
- 核心方法：以象取事，干支作功，宫位类象
- 分析路径：看干支组合之象→宫位类象→作功方向→断具体事象
- 经典引用：盲派口诀与实战案例

## 心理咨询师（现代积极心理学视角）
- 核心方法：性格优势识别 + 认知行为引导
- 分析路径：从十神性格特质→识别核心优势→给出可操作建议
- 关键原则：去宿命化、强调主观能动性、温暖鼓励

## 协作规则
1. 先各自独立分析，再融合共识
2. 有分歧时说明不同观点，给出综合判断
3. 每个关键结论至少有一条经典依据
4. 用通俗语言解释专业术语（括号注释法）
5. 始终强调"命理仅供参考，行动改变命运"
"""

CHAT_SYSTEM = """你是「知命先生」——一位温暖、专业、有趣的AI命理师。

## 你的人设
- 精通《渊海子平》《子平真诠》《滴天髓》《穷通宝鉴》《三命通会》五大经典
- 说话风格：像一位博学又亲切的长辈，专业但不晦涩，温暖但不油腻
- 会用生活化的比喻解释命理概念
- 适当引用经典原文，并翻译成大白话

## 对话规则
1. 首次对话：温暖问候，询问出生信息（年月日时、阳历/农历、性别）
2. 信息不全：友好追问，不催促
3. 收到完整信息：确认信息后告知正在排盘
4. 分析完成：先给一句话总结（层级1），再展开详细分析（层级2/3）
5. 后续问答：基于已有命盘回答，引用经典，给出可操作建议
6. 情感支持：遇到用户困扰，先共情再分析，语气温暖鼓励

## 输出风格
- 重要信息用 **加粗** 标注
- 用「」引用经典原文
- 段落清晰，不堆砌术语
- 不使用任何 emoji 或表情符号，保持文字的古朴感

## 红线
- 不替用户做决定，只提供参考视角
- 不宣扬宿命论，强调"了解自己，更好前行"
- 每次解读末尾提醒"仅供娱乐参考"
"""

BIRTH_EXTRACT_PROMPT = """从用户消息中提取出生信息。如果信息不完整，标记为null。

严格输出JSON（不要其他文字）：
{"year":数字或null,"month":数字或null,"day":数字或null,"hour":数字(0-23)或null,"calendar":"solar"或"lunar"或null,"gender":"male"或"female"或null,"is_leap":false,"needs_clarify":["需要追问的问题列表"]}

注意：
- "三点多"→hour=15（下午三点）
- "上午九点"→hour=9
- 如果没说公历农历，标记calendar=null
- 时辰映射：子23-1 丑1-3 寅3-5 卯5-7 辰7-9 巳9-11 午11-13 未13-15 申15-17 酉17-19 戌19-21 亥21-23
"""

DEEP_ANALYSIS_PROMPT = """请用多专家协作思维链(CoT)方法深度分析以下命盘。

## 命盘数据
{bazi_data}

## 分析步骤（请逐步推理）

### 第一步：基础判断
- 日主五行属性、生于什么月、得令得地得势情况

### 第二步：格局分析（格局专家视角）
- 月令透干定格局，成格条件，格局高低
- 引用《子平真诠》依据

### 第三步：调候分析（调候专家视角）
- 生于什么季节，寒暖燥湿如何
- 调候用神是什么
- 引用《穷通宝鉴》依据

### 第四步：象法推断（象法专家视角）
- 干支组合之象，宫位类象
- 具体事象推断

### 第五步：性格与心理（心理咨询师视角）
- 十神性格特质分析
- 核心优势与成长空间
- 积极正向的解读

### 第六步：综合融合
- 多视角共识与分歧
- 最终综合判断
- 可操作的人生建议

## 输出要求
- 逻辑清晰，层层递进
- 专业术语后括号注释大白话
- 每个关键结论有经典依据
- 语气温暖专业，像朋友聊天
- 避免宿命论，强调主观能动性
- 总字数1500-2500字
"""


@lru_cache(maxsize=1)
def _client() -> Optional[Any]:
    if not HAS_OPENAI:
        return None
    cfg = get_settings()
    if not cfg.api_key:
        return None
    return OpenAI(
        api_key=cfg.api_key,
        base_url=cfg.base_url or None,
        timeout=httpx.Timeout(60.0, connect=30.0) if httpx else 60.0,
        max_retries=3,
    )


# ── 对话式交互（核心新功能）──────────────────────────────

def extract_birth_info(messages: List[Dict]) -> Optional[Dict]:
    """从对话历史中提取出生信息"""
    client = _client()
    if not client:
        return None

    user_texts = " ".join(
        m["content"] for m in messages if m.get("role") == "user"
    )
    if not user_texts.strip():
        return None

    cfg = get_settings()
    try:
        resp = client.chat.completions.create(
            model=cfg.LLM_MODEL,
            messages=[
                {"role": "system", "content": BIRTH_EXTRACT_PROMPT},
                {"role": "user", "content": user_texts},
            ],
            max_tokens=500,
            temperature=0.1,
            timeout=cfg.LLM_TIMEOUT,
        )
        content = (resp.choices[0].message.content or "").strip()
        return _parse_json(content)
    except Exception as e:
        logger.error("[LLM] 提取出生信息失败: %s", e)
        return None


def chat_stream(
    messages: List[Dict],
    bazi_context: Optional[str] = None,
) -> Generator[str, None, None]:
    """流式对话 — 返回 SSE 格式的文本块"""
    client = _client()
    if not client:
        yield "data: 抱歉，AI服务暂时不可用，请稍后再试。\n\n"
        yield "data: [DONE]\n\n"
        return

    cfg = get_settings()
    system_msg = CHAT_SYSTEM
    if bazi_context:
        system_msg += f"\n\n## 当前命盘数据\n{bazi_context}"

    api_messages = [{"role": "system", "content": system_msg}]
    for m in messages:
        role = m.get("role", "user")
        if role in ("user", "assistant"):
            api_messages.append({"role": role, "content": m["content"]})

    try:
        stream = client.chat.completions.create(
            model=cfg.LLM_MODEL,
            messages=api_messages,
            max_tokens=cfg.LLM_MAX_TOKENS,
            temperature=cfg.LLM_TEMPERATURE,
            timeout=cfg.LLM_TIMEOUT,
            stream=True,
        )
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                text = chunk.choices[0].delta.content
                yield f"data: {json.dumps({'text': text}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"
    except Exception as e:
        logger.error("[LLM] 流式对话异常: %s", e)
        yield f"data: {json.dumps({'text': f'抱歉，生成过程中出现了问题：{e}'}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"


def generate_deep_analysis_stream(
    bazi: Dict, wuxing: Dict, daily: Dict, gender: str,
    dayun: Optional[Dict] = None, yearly: Optional[Dict] = None,
) -> Generator[str, None, None]:
    """流式生成深度多专家命盘分析"""
    client = _client()
    if not client:
        yield "data: [DONE]\n\n"
        return

    bazi_data = _format_bazi_context(bazi, wuxing, daily, gender, dayun, yearly)
    prompt = DEEP_ANALYSIS_PROMPT.format(bazi_data=bazi_data)
    cfg = get_settings()

    try:
        stream = client.chat.completions.create(
            model=cfg.LLM_MODEL,
            messages=[
                {"role": "system", "content": MULTI_EXPERT_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            max_tokens=cfg.LLM_MAX_TOKENS,
            temperature=cfg.LLM_TEMPERATURE,
            timeout=cfg.LLM_TIMEOUT,
            stream=True,
        )
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                text = chunk.choices[0].delta.content
                yield f"data: {json.dumps({'text': text}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"
    except Exception as e:
        logger.error("[LLM] 深度分析流式异常: %s", e)
        yield "data: [DONE]\n\n"


# ── 原有功能（保留兼容）──────────────────────────────────

def generate_reading(bazi: Dict, wuxing: Dict, daily: Dict, gender: str) -> Dict:
    client = _client()
    if not client:
        return _rule_based_reading(bazi, wuxing, daily, gender)

    prompt = _build_prompt(bazi, wuxing, daily, gender)
    cfg = get_settings()

    try:
        resp = client.chat.completions.create(
            model=cfg.LLM_MODEL,
            messages=[
                {"role": "system", "content": MULTI_EXPERT_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            max_tokens=cfg.LLM_MAX_TOKENS,
            temperature=cfg.LLM_TEMPERATURE,
            timeout=cfg.LLM_TIMEOUT,
        )
        content = (resp.choices[0].message.content or "").strip() if resp.choices else ""
        if not content:
            return _rule_based_reading(bazi, wuxing, daily, gender)

        parsed = _parse_json(content)
        return _normalize(parsed) if parsed else _rule_based_reading(bazi, wuxing, daily, gender)
    except Exception as e:
        logger.error("[LLM] 调用异常: %s", e)
        return _rule_based_reading(bazi, wuxing, daily, gender)


def generate_yearly_reading(bazi: Dict, wuxing: Dict, yearly: Dict, gender: str) -> Dict:
    client = _client()
    if not client:
        return _rule_based_yearly_reading(bazi, wuxing, yearly, gender)

    prompt = _build_yearly_prompt(bazi, wuxing, yearly, gender)
    cfg = get_settings()

    try:
        resp = client.chat.completions.create(
            model=cfg.LLM_MODEL,
            messages=[
                {"role": "system", "content": MULTI_EXPERT_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            max_tokens=cfg.LLM_MAX_TOKENS,
            temperature=cfg.LLM_TEMPERATURE,
            timeout=cfg.LLM_TIMEOUT,
        )
        content = (resp.choices[0].message.content or "").strip() if resp.choices else ""
        if not content:
            return _rule_based_yearly_reading(bazi, wuxing, yearly, gender)

        parsed = _parse_json(content)
        return _normalize_yearly(parsed) if parsed else _rule_based_yearly_reading(bazi, wuxing, yearly, gender)
    except Exception as e:
        logger.error("[LLM] 年度运势异常: %s", e)
        return _rule_based_yearly_reading(bazi, wuxing, yearly, gender)


# ── 格式化工具 ──────────────────────────────────────────

def _format_bazi_context(
    bazi: Dict, wuxing: Dict, daily: Dict, gender: str,
    dayun: Optional[Dict] = None, yearly: Optional[Dict] = None,
) -> str:
    pillars = bazi.get("pillars", {})
    bazi_str = " ".join(
        f"{pillars[k]['gan']}{pillars[k]['zhi']}"
        for k in ("year", "month", "day", "hour") if k in pillars
    )
    gender_cn = "男" if gender == "male" else "女"
    scores = daily.get("scores", {})

    lines = [
        f"性别：{gender_cn}",
        f"八字：{bazi_str}",
        f"日主：{wuxing.get('day_master', '')}（{wuxing.get('day_master_wuxing', bazi.get('day_master_wuxing', ''))}）",
        f"日主旺衰：{wuxing.get('strength', '')}",
        f"喜用神：{'、'.join(wuxing.get('favorable', []))}",
        f"忌神：{'、'.join(wuxing.get('unfavorable', []))}",
        f"缺失五行：{'、'.join(wuxing.get('missing', [])) or '无'}",
        f"五行分布：{json.dumps(wuxing.get('distribution', {}), ensure_ascii=False)}",
        f"纳音：{json.dumps(bazi.get('nayin', {}), ensure_ascii=False)}",
        f"十神：{json.dumps(bazi.get('shishen', {}), ensure_ascii=False)}",
        f"藏干：{json.dumps(bazi.get('canggan', {}), ensure_ascii=False)}",
        "",
        f"今日流日：{daily.get('ganzhi', '')}",
        f"今日综合评分：{scores.get('overall', 70)}",
    ]

    if dayun:
        cd = dayun.get("current_dayun", {})
        if cd:
            lines.append(f"当前大运：{cd.get('ganzhi', '')}（{cd.get('start_age', '')}~{cd.get('end_age', '')}岁）")
        lines.append(f"当前流年：{dayun.get('current_liunian', '')}")

    if yearly:
        lines.extend([
            f"流年干支：{yearly.get('ganzhi', '')}年",
            f"流年十神：{yearly.get('shishen', '')}",
            f"年度主题：{yearly.get('theme', '')}",
        ])

    return "\n".join(lines)


def _build_prompt(bazi: Dict, wuxing: Dict, daily: Dict, gender: str) -> str:
    pillars = bazi.get("pillars", {})
    bazi_str = " ".join(
        f"{pillars[k]['gan']}{pillars[k]['zhi']}"
        for k in ("year", "month", "day", "hour") if k in pillars
    )
    scores = daily.get("scores", {})
    almanac = daily.get("almanac", {})
    lucky = daily.get("lucky", {})
    gender_cn = "男" if gender == "male" else "女"

    return (
        f"请用多专家协作视角分析以下命盘今日运势。\n\n"
        f"【命主信息】\n"
        f"性别：{gender_cn}\n"
        f"八字：{bazi_str}\n"
        f"日主：{wuxing.get('day_master', '')}（{wuxing.get('strength', '')}）\n"
        f"喜用神：{'、'.join(wuxing.get('favorable', []))}\n"
        f"忌神：{'、'.join(wuxing.get('unfavorable', []))}\n\n"
        f"【今日流日】{daily.get('ganzhi', '')}  "
        f"日期：{daily.get('date', '')}（{daily.get('lunar_date', '')}）\n"
        f"【评分】综合{scores.get('overall', 70)} 事业{scores.get('career', 70)} "
        f"财运{scores.get('wealth', 70)} 感情{scores.get('love', 70)} 健康{scores.get('health', 70)}\n"
        f"【黄历】宜：{'、'.join(almanac.get('yi', []))} 忌：{'、'.join(almanac.get('ji', []))}\n"
        f"【幸运】色：{lucky.get('color', '')} 数：{lucky.get('number', '')} 方：{lucky.get('direction', '')}\n\n"
        f"请严格输出紧凑JSON：\n"
        f'{{"overview":"综合运势(120字内,融合格局/调候/象法三重视角,引用一句经典)",'
        f'"career":"事业运(80字内,具体可操作)",'
        f'"wealth":"财运(80字内)",'
        f'"love":"感情运(80字内)",'
        f'"health":"健康建议(80字内)",'
        f'"tips":"温馨小贴士(80字内,有趣有温度)"}}\n\n'
        f"要求：\n"
        f"1. 语气温暖专业，像朋友聊天\n"
        f"2. overview 要体现多专家融合视角\n"
        f"3. 每条建议有可操作性\n"
        f"4. 适当引用经典（用「」标注）"
    )


def _build_yearly_prompt(bazi: Dict, wuxing: Dict, yearly: Dict, gender: str) -> str:
    pillars = bazi.get("pillars", {})
    bazi_str = " ".join(
        f"{pillars[k]['gan']}{pillars[k]['zhi']}"
        for k in ("year", "month", "day", "hour") if k in pillars
    )
    scores = yearly.get("scores", {})
    taisui = yearly.get("taisui", {})
    gender_cn = "男" if gender == "male" else "女"

    taisui_str = "无"
    if taisui.get("has_conflict"):
        taisui_str = "、".join(t["type"] for t in taisui.get("types", []))

    monthly = yearly.get("monthly", [])
    top3 = sorted(monthly, key=lambda m: m.get("score", 0), reverse=True)[:3]
    bot3 = sorted(monthly, key=lambda m: m.get("score", 0))[:3]

    return (
        f"请用多专家协作视角分析以下命盘本年运势。\n\n"
        f"【命主】{gender_cn} 八字：{bazi_str} 日主：{wuxing.get('day_master', '')}({wuxing.get('strength', '')})\n"
        f"喜：{'、'.join(wuxing.get('favorable', []))} 忌：{'、'.join(wuxing.get('unfavorable', []))}\n\n"
        f"【流年】{yearly.get('year', '')} {yearly.get('ganzhi', '')}年 {yearly.get('shengxiao', '')}年\n"
        f"纳音：{yearly.get('nayin', '')} 十神：{yearly.get('shishen', '')} 主题：{yearly.get('theme', '')}\n"
        f"犯太岁：{taisui_str}\n"
        f"【评分】综合{scores.get('overall', 65)} 事业{scores.get('career', 65)} "
        f"财运{scores.get('wealth', 65)} 感情{scores.get('love', 65)} 健康{scores.get('health', 65)}\n"
        f"最佳月份：{'、'.join(str(m['name']) + '(' + str(m['score']) + ')' for m in top3)}\n"
        f"注意月份：{'、'.join(str(m['name']) + '(' + str(m['score']) + ')' for m in bot3)}\n\n"
        f"请严格输出紧凑JSON：\n"
        f'{{"yearly_overview":"年度总评(150字内,融合多专家视角,引经据典)",'
        f'"yearly_career":"事业(100字内)",'
        f'"yearly_wealth":"财运(100字内)",'
        f'"yearly_love":"感情(100字内)",'
        f'"yearly_health":"健康(100字内)",'
        f'"yearly_advice":"总体建议(100字内)",'
        f'"monthly_highlights":"月运重点(100字内)"}}\n'
    )


# ── 解析 & 兜底 ────────────────────────────────────────

def _parse_json(content: str) -> Optional[Dict]:
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

    stack, in_str, escape = [], False, False
    for ch in fragment:
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if ch in ("{", "["):
            stack.append("}" if ch == "{" else "]")
        elif ch in ("}", "]") and stack and stack[-1] == ch:
            stack.pop()

    fixed = fragment
    if in_str:
        fixed += '"'
    fixed += "".join(reversed(stack))
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    for i in range(len(fragment) - 1, 0, -1):
        if fragment[i] == "}":
            try:
                return json.loads(fragment[: i + 1])
            except json.JSONDecodeError:
                continue
    return None


def _normalize(raw: Dict) -> Dict:
    out = dict(DEFAULT_READING)
    for key in DEFAULT_READING:
        if isinstance(raw.get(key), str):
            out[key] = raw[key]
    return out


def _normalize_yearly(raw: Dict) -> Dict:
    out = dict(DEFAULT_YEARLY_READING)
    for key in DEFAULT_YEARLY_READING:
        if isinstance(raw.get(key), str):
            out[key] = raw[key]
    return out


def _rule_based_reading(bazi: Dict, wuxing: Dict, daily: Dict, gender: str) -> Dict:
    dm = wuxing.get("day_master", "日主")
    strength = wuxing.get("strength", "中和")
    favorable = wuxing.get("favorable", [])
    fav_str = "、".join(favorable) if favorable else "平衡"
    scores = daily.get("scores", {})
    overall = scores.get("overall", 70)
    gz = daily.get("ganzhi", "甲子")

    mood = "运势上佳" if overall >= 80 else ("运势平稳" if overall >= 60 else "运势偏低")

    return {
        "overview": f"今日{mood}。{dm}{strength}，喜{fav_str}，流日{gz}{'有利' if overall >= 65 else '略有冲击'}，综合{overall}分。",
        "career": f"事业{scores.get('career', 70)}分，{'适合推进重要项目' if scores.get('career', 70) >= 70 else '建议稳扎稳打'}。",
        "wealth": f"财运{scores.get('wealth', 70)}分，{'可把握投资机会' if scores.get('wealth', 70) >= 70 else '不宜冲动消费'}。",
        "love": f"感情{scores.get('love', 70)}分，{'桃花运不错' if scores.get('love', 70) >= 70 else '多沟通理解'}。",
        "health": f"健康{scores.get('health', 70)}分，{'状态良好' if scores.get('health', 70) >= 70 else '注意休息'}。",
        "tips": f"幸运色{daily.get('lucky', {}).get('color', '绿色')}，数字{daily.get('lucky', {}).get('number', 3)}，宜朝{daily.get('lucky', {}).get('direction', '东')}方。",
    }


def _rule_based_yearly_reading(bazi: Dict, wuxing: Dict, yearly: Dict, gender: str) -> Dict:
    dm = wuxing.get("day_master", "日主")
    strength = wuxing.get("strength", "中和")
    favorable = wuxing.get("favorable", [])
    fav_str = "、".join(favorable) if favorable else "平衡"
    scores = yearly.get("scores", {})
    overall = scores.get("overall", 65)
    gz = yearly.get("ganzhi", "甲子")
    theme = yearly.get("theme", "平稳过渡")
    shishen = yearly.get("shishen", "")
    taisui = yearly.get("taisui", {})

    mood = "运势大好" if overall >= 80 else ("运势平稳" if overall >= 65 else "运势偏低")
    taisui_text = ""
    if taisui.get("has_conflict"):
        types = "、".join(t["type"] for t in taisui.get("types", []))
        taisui_text = f"今年{types}，需多加谨慎。"

    monthly = yearly.get("monthly", [])
    top = sorted(monthly, key=lambda m: m.get("score", 0), reverse=True)[:2]
    bot = sorted(monthly, key=lambda m: m.get("score", 0))[:2]
    top_names = "、".join(m["name"] for m in top) if top else "上半年"
    bot_names = "、".join(m["name"] for m in bot) if bot else "下半年"

    return {
        "yearly_overview": f"{gz}年{mood}，{shishen}主导「{theme}」。{dm}{strength}喜{fav_str}。{taisui_text}综合{overall}分。",
        "yearly_career": f"事业{scores.get('career', 65)}分，{'适合拓展' if scores.get('career', 65) >= 70 else '稳扎稳打'}。",
        "yearly_wealth": f"财运{scores.get('wealth', 65)}分，{'把握机会' if scores.get('wealth', 65) >= 70 else '谨慎理财'}。",
        "yearly_love": f"感情{scores.get('love', 65)}分，{'桃花运旺' if scores.get('love', 65) >= 70 else '多沟通'}。",
        "yearly_health": f"健康{scores.get('health', 65)}分，{'保持运动' if scores.get('health', 65) >= 70 else '定期体检'}。",
        "yearly_advice": f"关键词「{theme}」，最佳期{top_names}，{bot_names}宜守成。",
        "monthly_highlights": f"重点{top_names}运势旺；{bot_names}需注意。",
    }
