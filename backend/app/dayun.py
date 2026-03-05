"""
大运流年排列：排大运 + 起运岁数 + 流年干支。
"""
import datetime as dt
import logging
from typing import Dict, List, Optional, Tuple

from .calendar_util import (
    TIAN_GAN, DI_ZHI, GAN_YINYANG,
    gan_index, zhi_index, index_to_ganzhi, get_nayin,
)
from .bazi import _get_shishen

logger = logging.getLogger("fortune.dayun")

# 十二节气（月份分界节气）的近似日期（日序号）
# 立春≈2/4, 惊蛰≈3/6, 清明≈4/5, 立夏≈5/6,
# 芒种≈6/6, 小暑≈7/7, 立秋≈8/8, 白露≈9/8,
# 寒露≈10/8, 立冬≈11/7, 大雪≈12/7, 小寒≈1/6
JIEQI_APPROX = [
    (2, 4), (3, 6), (4, 5), (5, 6), (6, 6), (7, 7),
    (8, 8), (9, 8), (10, 8), (11, 7), (12, 7), (1, 6),
]


def calculate_dayun(bazi: Dict, gender: str, birth_year: int) -> Dict:
    """
    排大运。

    规则:
    - 阳年男/阴年女 → 顺排
    - 阴年男/阳年女 → 逆排
    - 起运岁数 = 出生到最近节气的天数 / 3

    参数:
        bazi: calculate_bazi() 的返回值
        gender: "male" / "female"
        birth_year: 出生年份（阳历）
    """
    pillars = bazi['pillars']
    year_gan = pillars['year']['gan']
    month_gan = pillars['month']['gan']
    month_zhi = pillars['month']['zhi']
    day_master = bazi['day_master']

    # 判断顺逆
    year_yinyang = GAN_YINYANG[year_gan]
    is_yang_year = year_yinyang == '阳'
    is_male = gender == 'male'
    forward = (is_yang_year and is_male) or (not is_yang_year and not is_male)

    # 起运岁数（简化计算：取 3-8 之间的近似值）
    start_age = _calc_start_age(bazi, forward)

    # 排大运（从月柱出发，顺/逆推 10 步）
    month_gz_idx = ganzhi_to_idx(month_gan, month_zhi)
    dayun_list = []
    current_year = dt.date.today().year

    for step in range(1, 11):
        if forward:
            gz_idx = (month_gz_idx + step) % 60
        else:
            gz_idx = (month_gz_idx - step) % 60

        gan, zhi = index_to_ganzhi(gz_idx)
        s_age = start_age + (step - 1) * 10
        e_age = s_age + 9
        s_year = birth_year + s_age
        e_year = birth_year + e_age

        dayun_list.append({
            'start_age': s_age,
            'end_age': e_age,
            'start_year': s_year,
            'end_year': e_year,
            'gan': gan,
            'zhi': zhi,
            'ganzhi': f"{gan}{zhi}",
            'nayin': get_nayin(gan, zhi),
            'shishen_gan': _get_shishen(day_master, gan),
        })

    # 当前大运
    age_now = current_year - birth_year
    current_dayun = None
    for d in dayun_list:
        if d['start_age'] <= age_now <= d['end_age']:
            current_dayun = d
            break

    # 当前流年
    ly_gan, ly_zhi = index_to_ganzhi((current_year - 4) % 60)
    current_liunian = f"{ly_gan}{ly_zhi}"

    return {
        'start_age': start_age,
        'forward': forward,
        'current_dayun': current_dayun,
        'current_liunian': current_liunian,
        'current_liunian_shishen': _get_shishen(day_master, ly_gan),
        'list': dayun_list,
    }


def ganzhi_to_idx(gan: str, zhi: str) -> int:
    g = gan_index(gan)
    z = zhi_index(zhi)
    for i in range(60):
        if i % 10 == g and i % 12 == z:
            return i
    return 0


def _calc_start_age(bazi: Dict, forward: bool) -> int:
    """
    计算起运岁数。
    简化算法：根据出生日到最近节气的距离估算。
    精确算法需要查询实际节气时刻。
    """
    try:
        solar_str = bazi.get('solar_date', '')
        if not solar_str:
            return 5
        birth_date = dt.date.fromisoformat(solar_str)
        birth_month = birth_date.month

        if forward:
            next_jq = _next_jieqi(birth_date)
        else:
            next_jq = _prev_jieqi(birth_date)

        if next_jq:
            days_diff = abs((next_jq - birth_date).days)
            age = max(1, round(days_diff / 3))
            return min(age, 10)
    except Exception:
        pass
    return 5


def _next_jieqi(date: dt.date) -> Optional[dt.date]:
    """下一个节气的近似日期"""
    for m, d in JIEQI_APPROX:
        jq_date = dt.date(date.year, m, d)
        if jq_date > date:
            return jq_date
    return dt.date(date.year + 1, 2, 4)


def _prev_jieqi(date: dt.date) -> Optional[dt.date]:
    """上一个节气的近似日期"""
    for m, d in reversed(JIEQI_APPROX):
        jq_date = dt.date(date.year, m, d)
        if jq_date < date:
            return jq_date
    return dt.date(date.year - 1, 12, 7)
