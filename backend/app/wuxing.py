"""
五行旺衰分析与喜用神判定（旺衰法）。
"""
from typing import Dict, List, Tuple

from .calendar_util import (
    GAN_WUXING, GAN_YINYANG, ZHI_WUXING, ZHI_CANGGAN, CANGGAN_WEIGHT,
    WUXING_LIST, WUXING_SHENG, WUXING_KE,
    WUXING_COLOR, WUXING_NUMBER, WUXING_DIRECTION,
    YUELING_STRENGTH,
)


def analyze_wuxing(bazi: Dict) -> Dict:
    """
    五行旺衰分析 + 喜用神判定。

    参数: bazi — calculate_bazi() 的返回值
    返回: 五行分布、日主强弱、喜用神/忌神
    """
    pillars = bazi['pillars']
    day_master = bazi['day_master']
    dm_wuxing = bazi['day_master_wuxing']
    month_zhi = pillars['month']['zhi']

    # 1. 计算五行力量分布
    strength = _calc_wuxing_strength(pillars)

    # 2. 月令旺衰系数
    yueling_factor = YUELING_STRENGTH.get(dm_wuxing, {}).get(month_zhi, 1.0)

    # 3. 判断日主强弱
    dm_strength = strength.get(dm_wuxing, 0)
    total_strength = sum(strength.values()) or 1

    # 帮身力量 = 同类(比劫) + 生我(印)
    sheng_wo = [wx for wx, target in WUXING_SHENG.items() if target == dm_wuxing]
    help_strength = dm_strength + sum(strength.get(wx, 0) for wx in sheng_wo)

    # 克泄耗力量 = 我生(食伤) + 我克(财) + 克我(官杀)
    drain_strength = total_strength - help_strength

    # 综合判断
    ratio = help_strength / total_strength if total_strength else 0.5
    adjusted_ratio = ratio * yueling_factor

    if adjusted_ratio >= 0.55:
        dm_status = '偏强'
    elif adjusted_ratio >= 0.45:
        dm_status = '中和'
    else:
        dm_status = '偏弱'

    # 4. 喜用神判定（旺衰法）
    favorable, unfavorable = _determine_favorable(dm_wuxing, dm_status)

    # 5. 特殊格局检测
    pattern = _detect_special_pattern(strength, dm_wuxing, total_strength, yueling_factor)
    if pattern:
        favorable, unfavorable = _adjust_for_pattern(pattern, dm_wuxing, favorable, unfavorable)

    # 6. 五行缺失
    missing = [wx for wx in WUXING_LIST if strength.get(wx, 0) == 0]

    return {
        'distribution': {wx: round(strength.get(wx, 0), 2) for wx in WUXING_LIST},
        'day_master': f"{day_master}{dm_wuxing}",
        'day_master_wuxing': dm_wuxing,
        'strength': dm_status,
        'strength_ratio': round(adjusted_ratio, 3),
        'yueling_factor': yueling_factor,
        'favorable': favorable,
        'unfavorable': unfavorable,
        'missing': missing,
        'pattern': pattern,
    }


def _calc_wuxing_strength(pillars: Dict) -> Dict[str, float]:
    """量化八字中五行力量（天干 + 地支藏干加权）"""
    strength: Dict[str, float] = {wx: 0.0 for wx in WUXING_LIST}

    # 天干力量（每个天干 1.0 点）
    for name in ('year', 'month', 'day', 'hour'):
        gan = pillars[name]['gan']
        wx = GAN_WUXING[gan]
        strength[wx] += 1.0

    # 地支藏干力量（本气 0.6, 中气 0.3, 余气 0.1）
    for name in ('year', 'month', 'day', 'hour'):
        zhi = pillars[name]['zhi']
        cg_list = ZHI_CANGGAN.get(zhi, [])
        for i, cg in enumerate(cg_list):
            wx = GAN_WUXING[cg]
            weight = CANGGAN_WEIGHT[i] if i < len(CANGGAN_WEIGHT) else 0.05
            strength[wx] += weight

    return strength


def _determine_favorable(dm_wuxing: str, dm_status: str) -> Tuple[List[str], List[str]]:
    """根据日主旺衰判定喜用神/忌神"""
    sheng_wo = [wx for wx, target in WUXING_SHENG.items() if target == dm_wuxing]
    wo_sheng = WUXING_SHENG[dm_wuxing]
    ke_wo = [wx for wx, target in WUXING_KE.items() if target == dm_wuxing]
    wo_ke = WUXING_KE[dm_wuxing]

    if dm_status == '偏强':
        # 日主偏强 → 喜克泄耗：官杀(克我)、食伤(我生)、财星(我克)
        favorable = list(set(ke_wo + [wo_sheng, wo_ke]))
        unfavorable = list(set(sheng_wo + [dm_wuxing]))
    elif dm_status == '偏弱':
        # 日主偏弱 → 喜生扶：印星(生我)、比劫(同类)
        favorable = list(set(sheng_wo + [dm_wuxing]))
        unfavorable = list(set(ke_wo + [wo_sheng, wo_ke]))
    else:
        # 中和 → 轻微喜泄
        favorable = [wo_sheng, wo_ke]
        unfavorable = ke_wo[:1] if ke_wo else []

    return favorable, unfavorable


def _detect_special_pattern(
    strength: Dict[str, float], dm_wuxing: str, total: float, yueling: float
) -> str:
    """检测特殊格局"""
    dm_str = strength.get(dm_wuxing, 0)
    ratio = dm_str / total if total else 0

    if ratio >= 0.45 and yueling >= 1.2:
        return '从强'
    if ratio <= 0.08 and yueling <= 0.6:
        return '从弱'
    return ''


def _adjust_for_pattern(
    pattern: str, dm_wuxing: str,
    favorable: List[str], unfavorable: List[str]
) -> Tuple[List[str], List[str]]:
    """特殊格局调整喜忌"""
    sheng_wo = [wx for wx, target in WUXING_SHENG.items() if target == dm_wuxing]

    if pattern == '从强':
        favorable = list(set(sheng_wo + [dm_wuxing]))
        unfavorable = [wx for wx in WUXING_LIST if wx not in favorable]
    elif pattern == '从弱':
        ke_wo = [wx for wx, target in WUXING_KE.items() if target == dm_wuxing]
        wo_sheng = WUXING_SHENG[dm_wuxing]
        wo_ke = WUXING_KE[dm_wuxing]
        favorable = list(set(ke_wo + [wo_sheng, wo_ke]))
        unfavorable = list(set(sheng_wo + [dm_wuxing]))

    return favorable, unfavorable


def get_lucky_elements(wuxing_result: Dict) -> Dict:
    """根据喜用神五行获取幸运色/数字/方位"""
    favorable = wuxing_result.get('favorable', [])
    if not favorable:
        favorable = ['木']

    primary_wx = favorable[0]
    return {
        'color': WUXING_COLOR.get(primary_wx, ['绿色'])[0],
        'color_alt': WUXING_COLOR.get(primary_wx, ['绿色', '青色'])[-1],
        'number': WUXING_NUMBER.get(primary_wx, [3, 8])[0],
        'number_alt': WUXING_NUMBER.get(primary_wx, [3, 8])[-1],
        'direction': WUXING_DIRECTION.get(primary_wx, '东'),
    }
