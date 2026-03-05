"""
Pydantic 模型定义：API 请求/响应结构。
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict


# ── 请求模型 ──────────────────────────────────────────

class FortuneRequest(BaseModel):
    birth_date: str = Field(..., description="出生日期 YYYY-MM-DD")
    calendar_type: str = Field(default="solar", description="solar=阳历, lunar=农历")
    birth_hour: int = Field(..., ge=0, le=23, description="出生小时 0-23")
    gender: str = Field(..., description="male=男, female=女")
    is_leap_month: bool = Field(default=False, description="农历是否闰月")


class DailyRequest(BaseModel):
    birth_date: str
    calendar_type: str = "solar"
    birth_hour: int = Field(..., ge=0, le=23)
    gender: str
    is_leap_month: bool = False
    target_date: Optional[str] = Field(None, description="目标日期(默认今天)")


# ── 响应子模型 ────────────────────────────────────────

class Pillar(BaseModel):
    gan: str
    zhi: str


class BaziResult(BaseModel):
    pillars: Dict[str, Pillar]
    canggan: Dict[str, List[str]]
    shishen: Dict[str, Dict]
    nayin: Dict[str, str]
    day_master: str
    day_master_wuxing: str


class WuxingResult(BaseModel):
    distribution: Dict[str, float]
    day_master: str
    strength: str
    favorable: List[str]
    unfavorable: List[str]
    missing: List[str]


class DayunItem(BaseModel):
    start_age: int
    end_age: int
    start_year: int
    end_year: int
    gan: str
    zhi: str
    ganzhi: str
    shishen_gan: str


class DayunResult(BaseModel):
    start_age: int
    current_dayun: Optional[DayunItem] = None
    current_liunian: Optional[str] = None
    list: List[DayunItem]


class DailyScores(BaseModel):
    overall: int
    career: int
    wealth: int
    love: int
    health: int


class LuckyInfo(BaseModel):
    color: str
    color_alt: str
    number: int
    number_alt: int
    direction: str


class AlmanacInfo(BaseModel):
    yi: List[str]
    ji: List[str]
    star28: str = ""
    solar_term: str = ""
    lunar_date_str: str = ""


class DailyFortune(BaseModel):
    date: str
    lunar_date: str = ""
    ganzhi: str = ""
    scores: DailyScores
    lucky: LuckyInfo
    almanac: AlmanacInfo
    cautions: List[str]


class LLMReading(BaseModel):
    overview: str = ""
    career: str = ""
    wealth: str = ""
    love: str = ""
    health: str = ""
    tips: str = ""


class YearlyLLMReading(BaseModel):
    yearly_overview: str = ""
    yearly_career: str = ""
    yearly_wealth: str = ""
    yearly_love: str = ""
    yearly_health: str = ""
    yearly_advice: str = ""
    monthly_highlights: str = ""


class TaisuiType(BaseModel):
    type: str
    desc: str


class TaisuiInfo(BaseModel):
    has_conflict: bool = False
    types: List[TaisuiType] = []
    severity: int = 0
    shengxiao: str = ""
    taisui_shengxiao: str = ""


class YearlyScores(BaseModel):
    overall: int
    career: int
    wealth: int
    love: int
    health: int


class MonthlyOverview(BaseModel):
    month: int
    name: str
    ganzhi: str
    score: int
    shishen: str = ""
    hint: str = ""


class YearlyFortune(BaseModel):
    year: int
    ganzhi: str
    nayin: str = ""
    shengxiao: str = ""
    shishen: str = ""
    theme: str = ""
    taisui: TaisuiInfo
    scores: YearlyScores
    keywords: List[str] = []
    cautions: List[str] = []
    monthly: List[MonthlyOverview] = []


# ── 完整响应 ──────────────────────────────────────────

class FortuneResponse(BaseModel):
    bazi: BaziResult
    wuxing: WuxingResult
    dayun: DayunResult
    daily: DailyFortune
    reading: LLMReading
    yearly: Optional[YearlyFortune] = None
    yearly_reading: Optional[YearlyLLMReading] = None
