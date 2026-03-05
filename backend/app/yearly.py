"""
本年运势推算：流年与命局交叉分析 + 犯太岁检测 + 年度综合评分。
"""
import datetime as dt
import logging
from typing import Dict, List, Tuple

from .calendar_util import (
    TIAN_GAN, DI_ZHI, GAN_WUXING, ZHI_WUXING, GAN_YINYANG,
    LIU_CHONG, LIU_HE, SAN_XING, LIU_HAI,
    WUXING_SHENG, WUXING_KE,
    index_to_ganzhi, get_nayin,
)
from .bazi import _get_shishen

logger = logging.getLogger("fortune.yearly")

ZHI_SHENGXIAO = {
    '子': '鼠', '丑': '牛', '寅': '虎', '卯': '兔', '辰': '龙', '巳': '蛇',
    '午': '马', '未': '羊', '申': '猴', '酉': '鸡', '戌': '狗', '亥': '猪',
}

LIU_PO = {
    '子': '酉', '酉': '子', '丑': '辰', '辰': '丑',
    '寅': '亥', '亥': '寅', '卯': '午', '午': '卯',
    '巳': '申', '申': '巳', '未': '戌', '戌': '未',
}


def calculate_yearly(
    bazi: Dict,
    wuxing_result: Dict,
    gender: str,
    birth_year: int,
    target_year: int = None,
) -> Dict:
    """
    计算本年运势。

    参数:
        bazi: calculate_bazi() 结果
        wuxing_result: analyze_wuxing() 结果
        gender: "male" / "female"
        birth_year: 出生年份（阳历）
        target_year: 目标年份 (默认今年)
    """
    if target_year is None:
        target_year = dt.date.today().year

    ly_gan, ly_zhi = index_to_ganzhi((target_year - 4) % 60)
    ly_nayin = get_nayin(ly_gan, ly_zhi)

    pillars = bazi['pillars']
    day_master = bazi['day_master']
    favorable = wuxing_result.get('favorable', [])
    unfavorable = wuxing_result.get('unfavorable', [])
    year_zhi = pillars['year']['zhi']

    taisui = _check_taisui(year_zhi, ly_zhi)

    shishen = _get_shishen(day_master, ly_gan)
    theme = _get_yearly_theme(shishen, taisui)

    scores = _calc_yearly_scores(
        bazi, wuxing_result, ly_gan, ly_zhi, favorable, unfavorable, taisui, shishen,
    )

    keywords = _generate_keywords(scores, taisui, shishen, favorable, ly_gan, ly_zhi)

    cautions = _generate_yearly_cautions(
        bazi, wuxing_result, ly_gan, ly_zhi, taisui, scores,
    )

    monthly = _calc_monthly_overview(bazi, wuxing_result, target_year)

    return {
        'year': target_year,
        'ganzhi': f"{ly_gan}{ly_zhi}",
        'nayin': ly_nayin,
        'shengxiao': ZHI_SHENGXIAO.get(ly_zhi, ''),
        'shishen': shishen,
        'theme': theme,
        'taisui': taisui,
        'scores': scores,
        'keywords': keywords,
        'cautions': cautions,
        'monthly': monthly,
    }


def _check_taisui(year_zhi: str, ly_zhi: str) -> Dict:
    """检测犯太岁情况"""
    result = {
        'has_conflict': False,
        'types': [],
        'severity': 0,
        'shengxiao': ZHI_SHENGXIAO.get(year_zhi, ''),
        'taisui_shengxiao': ZHI_SHENGXIAO.get(ly_zhi, ''),
    }

    if year_zhi == ly_zhi:
        result['types'].append({'type': '值太岁', 'desc': '本命年，诸事宜慎'})
        result['severity'] += 3

    if LIU_CHONG.get(year_zhi) == ly_zhi:
        result['types'].append({'type': '冲太岁', 'desc': '动荡变化多，防破财伤身'})
        result['severity'] += 4

    if SAN_XING.get(year_zhi) == ly_zhi:
        result['types'].append({'type': '刑太岁', 'desc': '口舌是非多，注意人际'})
        result['severity'] += 3

    if LIU_HAI.get(year_zhi) == ly_zhi:
        result['types'].append({'type': '害太岁', 'desc': '暗中阻碍多，提防小人'})
        result['severity'] += 2

    if LIU_PO.get(year_zhi) == ly_zhi:
        result['types'].append({'type': '破太岁', 'desc': '破耗不聚财，凡事三思'})
        result['severity'] += 2

    result['has_conflict'] = len(result['types']) > 0
    result['severity'] = min(result['severity'], 5)
    return result


def _get_yearly_theme(shishen: str, taisui: Dict) -> str:
    """根据流年十神确定年度主题"""
    theme_map = {
        '正官': '事业晋升',
        '偏官': '开拓挑战',
        '正印': '学业贵人',
        '偏印': '灵感创新',
        '正财': '稳健聚财',
        '偏财': '投资机遇',
        '食神': '才华绽放',
        '伤官': '突破变革',
        '比肩': '合作竞争',
        '劫财': '人际博弈',
    }
    theme = theme_map.get(shishen, '平稳过渡')

    if taisui['has_conflict'] and taisui['severity'] >= 3:
        theme += '·宜守不宜攻'

    return theme


def _calc_yearly_scores(
    bazi: Dict, wuxing_result: Dict,
    ly_gan: str, ly_zhi: str,
    favorable: List[str], unfavorable: List[str],
    taisui: Dict, shishen: str,
) -> Dict:
    """计算年度各项评分"""
    pillars = bazi['pillars']
    day_master = bazi['day_master']

    # 基础分：流年五行与喜忌
    base = 65
    gan_wx = GAN_WUXING.get(ly_gan, '')
    zhi_wx = ZHI_WUXING.get(ly_zhi, '')

    if gan_wx in favorable:
        base += 12
    elif gan_wx in unfavorable:
        base -= 10

    if zhi_wx in favorable:
        base += 8
    elif zhi_wx in unfavorable:
        base -= 8

    # 太岁惩罚
    if taisui['has_conflict']:
        base -= taisui['severity'] * 3

    # 地支关系加成
    rel_score = 0
    for name in ('year', 'month', 'day', 'hour'):
        zhi = pillars[name]['zhi']
        if LIU_HE.get(zhi) == ly_zhi:
            rel_score += 4
        if LIU_CHONG.get(zhi) == ly_zhi:
            rel_score -= 6
        if SAN_XING.get(zhi) == ly_zhi:
            rel_score -= 3
        if LIU_HAI.get(zhi) == ly_zhi:
            rel_score -= 2

    base += _clamp(rel_score, -12, 12)

    # 事业
    career = base
    if shishen in ('正官', '偏官'):
        career += 10 if gan_wx in favorable else -3
    elif shishen in ('正印', '偏印'):
        career += 8

    # 财运
    wealth = base
    if shishen in ('正财', '偏财'):
        wealth += 12 if gan_wx in favorable else 3
    elif shishen in ('比肩', '劫财'):
        wealth -= 5

    # 感情
    love = base
    spouse_zhi = pillars['day']['zhi']
    if LIU_HE.get(spouse_zhi) == ly_zhi:
        love += 12
    elif LIU_CHONG.get(spouse_zhi) == ly_zhi:
        love -= 15
    if shishen in ('正财', '正官'):
        love += 5

    # 健康
    health = base + 3
    if taisui['has_conflict']:
        health -= taisui['severity'] * 2
    if gan_wx in unfavorable and zhi_wx in unfavorable:
        health -= 8

    overall = round(career * 0.3 + wealth * 0.25 + love * 0.2 + health * 0.25)

    return {
        'overall': _clamp(overall, 30, 95),
        'career': _clamp(career, 30, 95),
        'wealth': _clamp(wealth, 30, 95),
        'love': _clamp(love, 30, 95),
        'health': _clamp(health, 30, 95),
    }


def _generate_keywords(
    scores: Dict, taisui: Dict, shishen: str,
    favorable: List[str], ly_gan: str, ly_zhi: str,
) -> List[str]:
    """生成年度关键词"""
    keywords = []
    overall = scores['overall']

    if taisui['has_conflict']:
        for t in taisui['types']:
            keywords.append(t['type'])

    shishen_kw = {
        '正官': '贵人扶持', '偏官': '破旧立新',
        '正印': '学业进步', '偏印': '灵感迸发',
        '正财': '财运亨通', '偏财': '偏财入库',
        '食神': '才华横溢', '伤官': '锋芒毕露',
        '比肩': '贵人相助', '劫财': '竞争激烈',
    }
    kw = shishen_kw.get(shishen)
    if kw:
        keywords.append(kw)

    if overall >= 80:
        keywords.append('鸿运当头')
    elif overall >= 70:
        keywords.append('稳中向好')
    elif overall >= 55:
        keywords.append('平稳过渡')
    else:
        keywords.append('韬光养晦')

    gan_wx = GAN_WUXING.get(ly_gan, '')
    if gan_wx in favorable:
        keywords.append('喜神临门')

    return keywords[:5]


def _generate_yearly_cautions(
    bazi: Dict, wuxing_result: Dict,
    ly_gan: str, ly_zhi: str,
    taisui: Dict, scores: Dict,
) -> List[str]:
    """生成年度注意事项"""
    cautions = []
    unfavorable = wuxing_result.get('unfavorable', [])

    if taisui['has_conflict']:
        for t in taisui['types']:
            cautions.append(f"今年{t['type']}，{t['desc']}")

    gan_wx = GAN_WUXING.get(ly_gan, '')
    zhi_wx = ZHI_WUXING.get(ly_zhi, '')

    if gan_wx in unfavorable and zhi_wx in unfavorable:
        cautions.append("流年天地五行皆为忌神，全年行事宜稳健保守")

    if scores['health'] < 55:
        health_map = {'木': '肝胆', '火': '心血管', '土': '脾胃', '金': '呼吸系统', '水': '肾脏泌尿'}
        missing = wuxing_result.get('missing', [])
        if missing:
            organ = health_map.get(missing[0], '身体')
            cautions.append(f"全年注意{organ}方面的保养，定期体检")

    if scores['wealth'] < 55:
        cautions.append("财运偏弱之年，不宜大额投资或借贷")

    spouse_zhi = bazi['pillars']['day']['zhi']
    if LIU_CHONG.get(spouse_zhi) == ly_zhi:
        cautions.append("流年冲夫妻宫，感情上需多包容、勤沟通")

    if scores['overall'] >= 75:
        cautions.append("运势较旺之年，把握机遇但忌骄躁冒进")

    if not cautions:
        cautions.append("今年运势平稳，保持良好心态、稳步前行即可")

    return cautions[:5]


def _calc_monthly_overview(
    bazi: Dict, wuxing_result: Dict, target_year: int,
) -> List[Dict]:
    """计算12个月流月概览"""
    favorable = wuxing_result.get('favorable', [])
    unfavorable = wuxing_result.get('unfavorable', [])
    day_master = bazi['day_master']

    # 流年干支
    ly_idx = (target_year - 4) % 60
    ly_gan = TIAN_GAN[ly_idx % 10]

    # 用五虎遁月法推算正月干支，后续月份顺推
    # 年干→正月天干的映射
    yigan_to_yin_gan = {
        '甲': '丙', '己': '丙',
        '乙': '戊', '庚': '戊',
        '丙': '庚', '辛': '庚',
        '丁': '壬', '壬': '壬',
        '戊': '甲', '癸': '甲',
    }
    yin_gan = yigan_to_yin_gan.get(ly_gan, '甲')
    yin_gan_idx = TIAN_GAN.index(yin_gan)

    month_names = [
        '正月', '二月', '三月', '四月', '五月', '六月',
        '七月', '八月', '九月', '十月', '冬月', '腊月',
    ]
    month_zhi_list = ['寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥', '子', '丑']

    monthly = []
    for i in range(12):
        m_gan = TIAN_GAN[(yin_gan_idx + i) % 10]
        m_zhi = month_zhi_list[i]
        m_gan_wx = GAN_WUXING.get(m_gan, '')
        m_zhi_wx = ZHI_WUXING.get(m_zhi, '')

        score = 65
        if m_gan_wx in favorable:
            score += 10
        elif m_gan_wx in unfavorable:
            score -= 8
        if m_zhi_wx in favorable:
            score += 6
        elif m_zhi_wx in unfavorable:
            score -= 6

        # 流月与命局日支关系
        day_zhi = bazi['pillars']['day']['zhi']
        if LIU_HE.get(day_zhi) == m_zhi:
            score += 5
        elif LIU_CHONG.get(day_zhi) == m_zhi:
            score -= 8

        m_shishen = _get_shishen(day_master, m_gan)
        hint = _month_hint(m_shishen, score)

        monthly.append({
            'month': i + 1,
            'name': month_names[i],
            'ganzhi': f"{m_gan}{m_zhi}",
            'score': _clamp(score, 30, 95),
            'shishen': m_shishen,
            'hint': hint,
        })

    return monthly


def _month_hint(shishen: str, score: int) -> str:
    """生成月度简短提示"""
    if score >= 78:
        return '运势旺盛，适合进取'
    elif score >= 68:
        hint_map = {
            '正官': '贵人助力，利于晋升',
            '偏官': '挑战中有机遇',
            '正印': '学习进修佳月',
            '偏印': '灵感频现，宜创作',
            '正财': '收入稳步增长',
            '偏财': '偏财运不错',
            '食神': '才能发挥顺畅',
            '伤官': '表达欲强，宜收敛',
            '比肩': '合作运佳',
            '劫财': '防破财',
        }
        return hint_map.get(shishen, '运势平稳')
    elif score >= 55:
        return '平稳守成，不宜冒进'
    else:
        return '低调行事，以守为攻'


def _clamp(val: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, val))
