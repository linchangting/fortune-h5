"""
黄历引擎：当日宜忌、值日星神、吉凶时辰。
基于 cnlunar 提供的黄历数据。
"""
import datetime as dt
import logging
from typing import Dict, List, Optional

logger = logging.getLogger("fortune.almanac")


def get_almanac(date: dt.date) -> Dict:
    """
    获取指定日期的黄历数据。

    返回:
        yi: 宜事列表
        ji: 忌事列表
        star28: 二十八宿
        jianchu: 十二建除
        chongsha: 冲煞
        lucky_hours: 吉时列表
        solar_term: 节气(如有)
    """
    try:
        import cnlunar
        lunar = cnlunar.Lunar(dt.datetime(date.year, date.month, date.day, 12, 0))

        yi = _safe_list(getattr(lunar, 'goodThing', None))
        ji = _safe_list(getattr(lunar, 'badThing', None))

        star28 = ''
        try:
            star28 = lunar.get_today28Star() or ''
        except Exception:
            pass

        solar_term = ''
        try:
            st = getattr(lunar, 'todaySolarTerms', '')
            if st and st != '无':
                solar_term = st
        except Exception:
            pass

        lucky_gods = {}
        try:
            lucky_gods = lunar.get_luckyGodsDirection() or {}
        except Exception:
            pass

        twohour_list = []
        try:
            raw = getattr(lunar, 'twohour8CharList', [])
            if raw and isinstance(raw, (list, tuple)):
                twohour_list = [str(x) for x in raw]
        except Exception:
            pass

        lunar_date_str = ''
        try:
            lunar_date_str = f"{lunar.lunarMonthCn}{lunar.lunarDayCn}"
        except Exception:
            pass

        return {
            'yi': yi[:12],
            'ji': ji[:12],
            'star28': star28,
            'solar_term': solar_term,
            'lucky_gods': lucky_gods,
            'twohour_list': twohour_list,
            'lunar_date_str': lunar_date_str,
        }

    except ImportError:
        logger.warning("cnlunar 未安装，使用默认黄历数据")
        return _default_almanac()
    except Exception as e:
        logger.error("黄历计算异常: %s", e)
        return _default_almanac()


def _safe_list(obj) -> List[str]:
    if not obj:
        return []
    if isinstance(obj, str):
        return [s.strip() for s in obj.split(' ') if s.strip()]
    if isinstance(obj, (list, tuple)):
        return [str(x).strip() for x in obj if x]
    return []


def _default_almanac() -> Dict:
    return {
        'yi': ['祈福', '出行', '交易'],
        'ji': ['动土', '安葬'],
        'star28': '',
        'solar_term': '',
        'lucky_gods': {},
        'twohour_list': [],
        'lunar_date_str': '',
    }
