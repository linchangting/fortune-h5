"""
每日运势推算：流日与命局交叉分析 + 综合评分。
"""
import datetime as dt
import logging
import random
from typing import Dict, List

from .calendar_util import (
    TIAN_GAN, DI_ZHI, GAN_WUXING, ZHI_WUXING,
    LIU_CHONG, LIU_HE, SAN_XING, LIU_HAI,
    WUXING_SHENG, WUXING_KE,
    index_to_ganzhi,
)
from .bazi import _get_shishen
from .wuxing import get_lucky_elements
from .almanac import get_almanac

logger = logging.getLogger("fortune.daily")


def calculate_daily(
    bazi: Dict,
    wuxing_result: Dict,
    target_date: dt.date = None,
) -> Dict:
    """
    计算某日运势评分。

    参数:
        bazi: calculate_bazi() 结果
        wuxing_result: analyze_wuxing() 结果
        target_date: 目标日期 (默认今天)
    """
    if target_date is None:
        target_date = dt.date.today()

    # 1. 获取流日干支
    day_gz = _get_day_ganzhi(target_date)
    day_gan, day_zhi = day_gz

    # 2. 获取黄历
    almanac = get_almanac(target_date)

    # 3. 获取幸运元素
    lucky = get_lucky_elements(wuxing_result)

    # 4. 计算各项评分
    pillars = bazi['pillars']
    day_master = bazi['day_master']
    favorable = wuxing_result.get('favorable', [])
    unfavorable = wuxing_result.get('unfavorable', [])

    base_score = _calc_base_score(day_gan, day_zhi, favorable, unfavorable)
    relation_score = _calc_relation_score(pillars, day_gan, day_zhi)

    career_score = _calc_career_score(bazi, day_gan, day_zhi, favorable, base_score)
    wealth_score = _calc_wealth_score(bazi, day_gan, day_zhi, favorable, base_score)
    love_score = _calc_love_score(bazi, day_gan, day_zhi, base_score)
    health_score = _calc_health_score(bazi, wuxing_result, day_gan, day_zhi, base_score)

    overall = _weighted_average(career_score, wealth_score, love_score, health_score)
    overall = _clamp(overall + relation_score, 30, 98)

    career_score = _clamp(career_score + relation_score // 2, 30, 98)
    wealth_score = _clamp(wealth_score + relation_score // 2, 30, 98)
    love_score = _clamp(love_score + relation_score // 3, 30, 98)
    health_score = _clamp(health_score + relation_score // 3, 30, 98)

    # 5. 注意事项
    cautions = _generate_cautions(
        bazi, wuxing_result, day_gan, day_zhi, almanac,
        overall, health_score,
    )

    # 6. 农历日期
    lunar_str = almanac.get('lunar_date_str', '')

    return {
        'date': target_date.isoformat(),
        'lunar_date': lunar_str,
        'ganzhi': f"{day_gan}{day_zhi}",
        'scores': {
            'overall': overall,
            'career': career_score,
            'wealth': wealth_score,
            'love': love_score,
            'health': health_score,
        },
        'lucky': lucky,
        'almanac': {
            'yi': almanac.get('yi', []),
            'ji': almanac.get('ji', []),
            'star28': almanac.get('star28', ''),
            'solar_term': almanac.get('solar_term', ''),
            'lunar_date_str': lunar_str,
        },
        'cautions': cautions,
    }


def _get_day_ganzhi(date: dt.date):
    """获取某日天干地支"""
    try:
        import cnlunar
        lunar = cnlunar.Lunar(dt.datetime(date.year, date.month, date.day, 12, 0))
        gz = lunar.day8Char
        return gz[0], gz[1]
    except Exception:
        ref = dt.date(2000, 1, 7)  # 甲子日
        delta = (date - ref).days
        idx = delta % 60
        return TIAN_GAN[idx % 10], DI_ZHI[idx % 12]


def _calc_base_score(
    day_gan: str, day_zhi: str,
    favorable: List[str], unfavorable: List[str],
) -> int:
    """基础分：流日五行与喜忌神的关系"""
    score = 65  # 基准分

    gan_wx = GAN_WUXING.get(day_gan, '')
    zhi_wx = ZHI_WUXING.get(day_zhi, '')

    if gan_wx in favorable:
        score += 10
    elif gan_wx in unfavorable:
        score -= 10

    if zhi_wx in favorable:
        score += 8
    elif zhi_wx in unfavorable:
        score -= 8

    return score


def _calc_relation_score(pillars: Dict, day_gan: str, day_zhi: str) -> int:
    """命局地支与流日地支的冲合刑害关系"""
    score = 0
    for name in ('year', 'month', 'day', 'hour'):
        zhi = pillars[name]['zhi']

        if LIU_HE.get(zhi) == day_zhi:
            score += 5
        if LIU_CHONG.get(zhi) == day_zhi:
            score -= 8 if name == 'day' else 5
        if SAN_XING.get(zhi) == day_zhi:
            score -= 4
        if LIU_HAI.get(zhi) == day_zhi:
            score -= 3

    return _clamp(score, -15, 15)


def _calc_career_score(
    bazi: Dict, day_gan: str, day_zhi: str,
    favorable: List[str], base: int,
) -> int:
    """事业运：偏重官星/印星"""
    score = base
    day_master = bazi['day_master']

    shishen = _get_shishen(day_master, day_gan)
    if shishen in ('正官', '偏官'):
        if GAN_WUXING[day_gan] in favorable:
            score += 12
        else:
            score -= 5
    elif shishen in ('正印', '偏印'):
        score += 8

    seed = hash(f"career_{bazi['solar_date']}_{day_gan}{day_zhi}") % 7
    score += seed - 3
    return score


def _calc_wealth_score(
    bazi: Dict, day_gan: str, day_zhi: str,
    favorable: List[str], base: int,
) -> int:
    """财运：偏重财星"""
    score = base
    day_master = bazi['day_master']

    shishen = _get_shishen(day_master, day_gan)
    if shishen in ('正财', '偏财'):
        if GAN_WUXING[day_gan] in favorable:
            score += 15
        else:
            score += 5
    elif shishen in ('比肩', '劫财'):
        score -= 5

    seed = hash(f"wealth_{bazi['solar_date']}_{day_gan}{day_zhi}") % 7
    score += seed - 3
    return score


def _calc_love_score(bazi: Dict, day_gan: str, day_zhi: str, base: int) -> int:
    """感情运：偏重日支（夫妻宫）"""
    score = base
    spouse_palace = bazi['pillars']['day']['zhi']

    if LIU_HE.get(spouse_palace) == day_zhi:
        score += 12
    elif LIU_CHONG.get(spouse_palace) == day_zhi:
        score -= 15

    seed = hash(f"love_{bazi['solar_date']}_{day_gan}{day_zhi}") % 7
    score += seed - 3
    return score


def _calc_health_score(
    bazi: Dict, wuxing_result: Dict,
    day_gan: str, day_zhi: str, base: int,
) -> int:
    """健康运：偏重五行平衡度 + 忌神激活"""
    score = base + 5
    unfavorable = wuxing_result.get('unfavorable', [])

    gan_wx = GAN_WUXING.get(day_gan, '')
    zhi_wx = ZHI_WUXING.get(day_zhi, '')

    if gan_wx in unfavorable and zhi_wx in unfavorable:
        score -= 12
    elif gan_wx in unfavorable or zhi_wx in unfavorable:
        score -= 5

    seed = hash(f"health_{bazi['solar_date']}_{day_gan}{day_zhi}") % 5
    score += seed - 2
    return score


def _weighted_average(career: int, wealth: int, love: int, health: int) -> int:
    return round(career * 0.3 + wealth * 0.25 + love * 0.2 + health * 0.25)


def _clamp(val: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, val))


def _generate_cautions(
    bazi: Dict, wuxing_result: Dict,
    day_gan: str, day_zhi: str,
    almanac: Dict, overall: int, health: int,
) -> List[str]:
    """生成今日注意事项"""
    cautions = []
    unfavorable = wuxing_result.get('unfavorable', [])
    gan_wx = GAN_WUXING.get(day_gan, '')
    zhi_wx = ZHI_WUXING.get(day_zhi, '')

    spouse_zhi = bazi['pillars']['day']['zhi']

    if LIU_CHONG.get(spouse_zhi) == day_zhi:
        cautions.append("今日与夫妻宫相冲，感情上宜多沟通、少争执")

    if gan_wx in unfavorable and zhi_wx in unfavorable:
        wx_name = gan_wx
        cautions.append(f"今日{wx_name}气偏旺且为忌神，行事宜谨慎保守")

    if health < 60:
        health_map = {'木': '肝胆', '火': '心血管', '土': '脾胃', '金': '呼吸系统', '水': '肾脏'}
        weak_wx = wuxing_result.get('missing', [])
        if weak_wx:
            organ = health_map.get(weak_wx[0], '身体')
            cautions.append(f"注意{organ}方面的养护，避免过度劳累")

    ji_list = almanac.get('ji', [])
    if '动土' in ji_list:
        cautions.append("黄历忌动土，不宜开工装修")
    if '远行' in ji_list or '出行' in ji_list:
        cautions.append("今日不宜长途出行")

    if overall < 55:
        cautions.append("今日运势偏低，建议以守为攻、低调行事")

    if not cautions:
        cautions.append("今日运势平稳，正常安排即可")

    return cautions[:4]
