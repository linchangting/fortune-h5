"""
八字排盘核心引擎：四柱排盘 + 藏干 + 十神 + 纳音。
使用 cnlunar 作为底层历法库，自行实现命理推算逻辑。
"""
import datetime as dt
import logging
from typing import Dict, List, Optional, Tuple

from .calendar_util import (
    TIAN_GAN, DI_ZHI, GAN_WUXING, GAN_YINYANG,
    ZHI_CANGGAN, NAYIN_TABLE,
    gan_index, zhi_index, ganzhi_to_index, get_nayin,
    hour_to_shichen_zhi,
)

logger = logging.getLogger("fortune.bazi")

# ── 五虎遁月法：年干 → 寅月(正月)天干起始 ──────────
WUHU_DUN_YUE = {
    '甲': '丙', '己': '丙',  # 甲己之年丙作首
    '乙': '戊', '庚': '戊',  # 乙庚之年戊为头
    '丙': '庚', '辛': '庚',  # 丙辛之年庚为上
    '丁': '壬', '壬': '壬',  # 丁壬之年壬为始
    '戊': '甲', '癸': '甲',  # 戊癸之年甲为源
}

# ── 五鼠遁时法：日干 → 子时天干起始 ──────────────────
WUSHU_DUN_SHI = {
    '甲': '甲', '己': '甲',  # 甲己还加甲
    '乙': '丙', '庚': '丙',  # 乙庚丙作初
    '丙': '戊', '辛': '戊',  # 丙辛从戊起
    '丁': '庚', '壬': '庚',  # 丁壬庚子居
    '戊': '壬', '癸': '壬',  # 戊癸何方发,壬子是真途
}

# ── 十神名称 ──────────────────────────────────────────
SHISHEN_NAMES = {
    ('同', '同'): '比肩', ('同', '异'): '劫财',
    ('生我', '同'): '偏印', ('生我', '异'): '正印',
    ('我生', '同'): '食神', ('我生', '异'): '伤官',
    ('克我', '同'): '偏官', ('克我', '异'): '正官',
    ('我克', '同'): '偏财', ('我克', '异'): '正财',
}


def _get_shishen(day_gan: str, target_gan: str) -> str:
    """计算日干与目标天干的十神关系"""
    wx_day = GAN_WUXING[day_gan]
    wx_target = GAN_WUXING[target_gan]
    yy_day = GAN_YINYANG[day_gan]
    yy_target = GAN_YINYANG[target_gan]

    same_yy = '同' if yy_day == yy_target else '异'

    from .calendar_util import WUXING_SHENG, WUXING_KE
    if wx_day == wx_target:
        return SHISHEN_NAMES[('同', same_yy)]
    elif WUXING_SHENG.get(wx_target) == wx_day:
        return SHISHEN_NAMES[('生我', same_yy)]
    elif WUXING_SHENG.get(wx_day) == wx_target:
        return SHISHEN_NAMES[('我生', same_yy)]
    elif WUXING_KE.get(wx_target) == wx_day:
        return SHISHEN_NAMES[('克我', same_yy)]
    elif WUXING_KE.get(wx_day) == wx_target:
        return SHISHEN_NAMES[('我克', same_yy)]
    return '比肩'


def _calc_hour_gan(day_gan: str, hour_zhi: str) -> str:
    """五鼠遁时法：从日干推算时辰天干"""
    start_gan = WUSHU_DUN_SHI[day_gan]
    start_idx = gan_index(start_gan)
    zhi_offset = zhi_index(hour_zhi)
    return TIAN_GAN[(start_idx + zhi_offset) % 10]


def _calc_month_gan(year_gan: str, month_zhi: str) -> str:
    """五虎遁月法：从年干推算月天干"""
    start_gan = WUHU_DUN_YUE[year_gan]
    start_idx = gan_index(start_gan)
    month_offset = (zhi_index(month_zhi) - 2) % 12  # 寅=0 起
    return TIAN_GAN[(start_idx + month_offset) % 10]


def calculate_bazi(
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    calendar_type: str = "solar",
    is_leap_month: bool = False,
) -> Dict:
    """
    完整八字排盘。

    参数:
        birth_year/month/day: 出生日期
        birth_hour: 出生小时 (0-23)
        calendar_type: "solar" 阳历 / "lunar" 农历
        is_leap_month: 农历是否闰月

    返回:
        包含四柱、藏干、十神、纳音的完整八字数据
    """
    # 1. 统一转为阳历
    if calendar_type == "lunar":
        from .calendar_util import lunar_to_solar
        solar_date = lunar_to_solar(birth_year, birth_month, birth_day, is_leap_month)
        if not solar_date:
            raise ValueError(f"无效的农历日期: {birth_year}年{birth_month}月{birth_day}日")
        solar_year, solar_month, solar_day = solar_date.year, solar_date.month, solar_date.day
    else:
        solar_year, solar_month, solar_day = birth_year, birth_month, birth_day

    # 2. 处理 23:00 子时归次日
    actual_date = dt.date(solar_year, solar_month, solar_day)
    if birth_hour >= 23:
        actual_date += dt.timedelta(days=1)

    # 3. 用 cnlunar 获取四柱基础数据
    try:
        import cnlunar
        adjusted_hour = 0 if birth_hour >= 23 else birth_hour
        lunar_obj = cnlunar.Lunar(
            dt.datetime(actual_date.year, actual_date.month, actual_date.day,
                        max(adjusted_hour, 0), 30)
        )

        year_gz = lunar_obj.year8Char
        month_gz = lunar_obj.month8Char
        day_gz = lunar_obj.day8Char

        year_gan, year_zhi = year_gz[0], year_gz[1]
        month_gan, month_zhi = month_gz[0], month_gz[1]
        day_gan, day_zhi = day_gz[0], day_gz[1]

        lunar_info = {
            'year': lunar_obj.lunarYear,
            'month': lunar_obj.lunarMonth,
            'day': lunar_obj.lunarDay,
            'is_leap': lunar_obj.isLunarLeapMonth,
            'month_cn': lunar_obj.lunarMonthCn,
            'day_cn': lunar_obj.lunarDayCn,
        }
    except Exception as e:
        logger.warning("cnlunar 不可用，使用简化计算: %s", e)
        year_gan, year_zhi = _fallback_year_ganzhi(actual_date.year)
        month_gan, month_zhi = _fallback_month_ganzhi(year_gan, actual_date.month)
        day_gan, day_zhi = _fallback_day_ganzhi(actual_date)
        lunar_info = None

    # 4. 时柱：自行用五鼠遁时法计算（更精确控制）
    hour_zhi = hour_to_shichen_zhi(birth_hour)
    hour_gan = _calc_hour_gan(day_gan, hour_zhi)

    # 5. 组装四柱
    pillars = {
        'year': {'gan': year_gan, 'zhi': year_zhi},
        'month': {'gan': month_gan, 'zhi': month_zhi},
        'day': {'gan': day_gan, 'zhi': day_zhi},
        'hour': {'gan': hour_gan, 'zhi': hour_zhi},
    }

    # 6. 藏干
    canggan = {}
    for name, p in pillars.items():
        canggan[name] = ZHI_CANGGAN.get(p['zhi'], [])

    # 7. 十神（以日干为"我"）
    shishen = {}
    for name, p in pillars.items():
        if name == 'day':
            shishen[name] = {'gan': '日主', 'canggan': [
                _get_shishen(day_gan, cg) for cg in canggan[name]
            ]}
        else:
            shishen[name] = {
                'gan': _get_shishen(day_gan, p['gan']),
                'canggan': [_get_shishen(day_gan, cg) for cg in canggan[name]],
            }

    # 8. 纳音
    nayin = {
        name: get_nayin(p['gan'], p['zhi'])
        for name, p in pillars.items()
    }

    return {
        'pillars': pillars,
        'canggan': canggan,
        'shishen': shishen,
        'nayin': nayin,
        'day_master': day_gan,
        'day_master_wuxing': GAN_WUXING[day_gan],
        'day_master_yinyang': GAN_YINYANG[day_gan],
        'solar_date': actual_date.isoformat(),
        'lunar_info': lunar_info,
        'birth_hour': birth_hour,
    }


# ── 回退计算（cnlunar 不可用时）──────────────────────

def _fallback_year_ganzhi(year: int) -> Tuple[str, str]:
    g = (year - 4) % 10
    z = (year - 4) % 12
    return TIAN_GAN[g], DI_ZHI[z]


def _fallback_month_ganzhi(year_gan: str, solar_month: int) -> Tuple[str, str]:
    month_zhi_offset = (solar_month + 1) % 12  # 简化：1月→寅
    if solar_month >= 2:
        month_zhi_offset = (solar_month) % 12
    month_zhi = DI_ZHI[(solar_month + 1) % 12]
    month_gan = _calc_month_gan(year_gan, month_zhi)
    return month_gan, month_zhi


def _fallback_day_ganzhi(date: dt.date) -> Tuple[str, str]:
    """简化日柱计算 (基于已知参考日)"""
    ref_date = dt.date(2000, 1, 7)  # 2000年1月7日 = 甲子日
    delta = (date - ref_date).days
    idx = delta % 60
    return TIAN_GAN[idx % 10], DI_ZHI[idx % 12]
