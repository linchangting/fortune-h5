"""
八字算命 H5 - FastAPI 后端
支持：传统排盘 API + AI 对话式交互（SSE 流式）
"""
import asyncio
import datetime as dt
import json
import logging

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .config import get_settings
from .models import FortuneRequest, DailyRequest, ChatRequest, FortuneResponse
from . import bazi as bazi_mod
from . import wuxing as wuxing_mod
from . import dayun as dayun_mod
from . import daily as daily_mod
from . import yearly as yearly_mod
from . import llm as llm_mod
from .calendar_util import solar_to_lunar, lunar_to_solar

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("fortune.main")

cfg = get_settings()

app = FastAPI(title="八字算命 H5 API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cfg.cors_origins,
    allow_credentials=False,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok", "has_api_key": bool(cfg.api_key), "version": "2.0.0"}


# ── 对话式交互（核心新功能）────────────────────────────

@app.post("/api/chat")
async def chat(req: ChatRequest):
    """AI 命理师对话 — SSE 流式响应"""
    messages = [{"role": m.role, "content": m.content} for m in req.messages]

    bazi_context = None
    if req.fortune_data:
        bazi_context = json.dumps(req.fortune_data, ensure_ascii=False)

    def event_stream():
        yield from llm_mod.chat_stream(messages, bazi_context)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/chat/extract-birth")
async def extract_birth(req: ChatRequest):
    """从对话历史中提取出生信息"""
    messages = [{"role": m.role, "content": m.content} for m in req.messages]
    info = await asyncio.to_thread(llm_mod.extract_birth_info, messages)
    return {"birth_info": info}


@app.post("/api/fortune/deep-analysis")
async def deep_analysis(req: FortuneRequest):
    """深度多专家命盘分析 — SSE 流式响应"""
    try:
        year, month, day = _parse_date(req.birth_date)
    except ValueError as e:
        raise HTTPException(400, str(e))

    if req.gender not in ("male", "female"):
        raise HTTPException(400, "gender 必须为 male 或 female")

    try:
        bazi_result = await asyncio.to_thread(
            bazi_mod.calculate_bazi,
            year, month, day, req.birth_hour,
            req.calendar_type, req.is_leap_month,
        )
    except Exception as e:
        raise HTTPException(400, f"排盘失败: {e}")

    wuxing_result = await asyncio.to_thread(wuxing_mod.analyze_wuxing, bazi_result)

    birth_year = year
    if req.calendar_type == "lunar":
        sd = lunar_to_solar(year, month, day, req.is_leap_month)
        if sd:
            birth_year = sd.year

    dayun_result = await asyncio.to_thread(
        dayun_mod.calculate_dayun, bazi_result, req.gender, birth_year,
    )
    daily_result = await asyncio.to_thread(
        daily_mod.calculate_daily, bazi_result, wuxing_result,
    )
    yearly_result = await asyncio.to_thread(
        yearly_mod.calculate_yearly,
        bazi_result, wuxing_result, req.gender, birth_year,
    )

    def event_stream():
        yield from llm_mod.generate_deep_analysis_stream(
            bazi_result, wuxing_result, daily_result, req.gender,
            dayun_result, yearly_result,
        )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── 传统 API（保持兼容）────────────────────────────────

@app.post("/api/fortune")
async def fortune(req: FortuneRequest):
    """完整排盘 + 今日运势 + LLM 解读"""
    try:
        year, month, day = _parse_date(req.birth_date)
    except ValueError as e:
        raise HTTPException(400, str(e))

    if req.gender not in ("male", "female"):
        raise HTTPException(400, "gender 必须为 male 或 female")

    try:
        bazi_result = await asyncio.to_thread(
            bazi_mod.calculate_bazi,
            year, month, day, req.birth_hour,
            req.calendar_type, req.is_leap_month,
        )
    except Exception as e:
        logger.error("排盘失败: %s", e)
        raise HTTPException(400, f"排盘失败: {e}")

    wuxing_result = await asyncio.to_thread(wuxing_mod.analyze_wuxing, bazi_result)

    birth_year = year
    if req.calendar_type == "lunar":
        sd = lunar_to_solar(year, month, day, req.is_leap_month)
        if sd:
            birth_year = sd.year

    dayun_result = await asyncio.to_thread(
        dayun_mod.calculate_dayun, bazi_result, req.gender, birth_year,
    )
    daily_result = await asyncio.to_thread(
        daily_mod.calculate_daily, bazi_result, wuxing_result,
    )
    yearly_result = await asyncio.to_thread(
        yearly_mod.calculate_yearly,
        bazi_result, wuxing_result, req.gender, birth_year,
    )
    reading = await asyncio.to_thread(
        llm_mod.generate_reading,
        bazi_result, wuxing_result, daily_result, req.gender,
    )
    yearly_reading = await asyncio.to_thread(
        llm_mod.generate_yearly_reading,
        bazi_result, wuxing_result, yearly_result, req.gender,
    )

    return _build_response(
        bazi_result, wuxing_result, dayun_result,
        daily_result, reading, yearly_result, yearly_reading,
    )


@app.post("/api/fortune/daily")
async def fortune_daily(req: DailyRequest):
    """每日运势"""
    try:
        year, month, day = _parse_date(req.birth_date)
    except ValueError as e:
        raise HTTPException(400, str(e))

    target = dt.date.today()
    if req.target_date:
        try:
            target = dt.date.fromisoformat(req.target_date)
        except ValueError:
            raise HTTPException(400, "target_date 格式错误")

    try:
        bazi_result = await asyncio.to_thread(
            bazi_mod.calculate_bazi,
            year, month, day, req.birth_hour,
            req.calendar_type, req.is_leap_month,
        )
    except Exception as e:
        raise HTTPException(400, f"排盘失败: {e}")

    wuxing_result = await asyncio.to_thread(wuxing_mod.analyze_wuxing, bazi_result)
    daily_result = await asyncio.to_thread(
        daily_mod.calculate_daily, bazi_result, wuxing_result, target,
    )
    reading = await asyncio.to_thread(
        llm_mod.generate_reading,
        bazi_result, wuxing_result, daily_result, req.gender,
    )

    birth_year = year
    if req.calendar_type == "lunar":
        sd = lunar_to_solar(year, month, day, req.is_leap_month)
        if sd:
            birth_year = sd.year

    dayun_result = await asyncio.to_thread(
        dayun_mod.calculate_dayun, bazi_result, req.gender, birth_year,
    )
    yearly_result = await asyncio.to_thread(
        yearly_mod.calculate_yearly,
        bazi_result, wuxing_result, req.gender, birth_year,
    )
    yearly_reading = await asyncio.to_thread(
        llm_mod.generate_yearly_reading,
        bazi_result, wuxing_result, yearly_result, req.gender,
    )

    return _build_response(
        bazi_result, wuxing_result, dayun_result,
        daily_result, reading, yearly_result, yearly_reading,
    )


@app.get("/api/calendar/convert")
async def calendar_convert(
    date: str = Query(..., description="日期 YYYY-MM-DD"),
    type: str = Query("solar_to_lunar", description="solar_to_lunar / lunar_to_solar"),
    is_leap: bool = Query(False),
):
    try:
        y, m, d = _parse_date(date)
    except ValueError as e:
        raise HTTPException(400, str(e))

    if type == "solar_to_lunar":
        result = solar_to_lunar(y, m, d)
        return {"type": "lunar", "result": result}
    elif type == "lunar_to_solar":
        sd = lunar_to_solar(y, m, d, is_leap)
        if sd:
            return {"type": "solar", "result": {"year": sd.year, "month": sd.month, "day": sd.day}}
        raise HTTPException(400, "无效的农历日期")
    else:
        raise HTTPException(400, "type 必须为 solar_to_lunar 或 lunar_to_solar")


@app.get("/api/calendar/lunar-months")
async def lunar_months(year: int = Query(..., ge=1940, le=2100)):
    months = []
    lunar_month_names = [
        "", "正月", "二月", "三月", "四月", "五月", "六月",
        "七月", "八月", "九月", "十月", "冬月", "腊月",
    ]

    for m in range(1, 13):
        days = _get_lunar_month_days(year, m, False)
        months.append({
            "month": m, "name": lunar_month_names[m],
            "days": days, "is_leap": False,
        })

    leap_month = _get_leap_month(year)
    if leap_month:
        days = _get_lunar_month_days(year, leap_month, True)
        insert_idx = leap_month
        months.insert(insert_idx, {
            "month": leap_month, "name": f"闰{lunar_month_names[leap_month]}",
            "days": days, "is_leap": True,
        })

    from .calendar_util import get_year_ganzhi
    gan, zhi = get_year_ganzhi(year)

    return {
        "year": year,
        "year_ganzhi": f"{gan}{zhi}",
        "months": months,
    }


# ── 内部工具 ──────────────────────────────────────────

def _parse_date(s: str):
    parts = s.split("-")
    if len(parts) != 3:
        raise ValueError("日期格式错误，请使用 YYYY-MM-DD")
    return int(parts[0]), int(parts[1]), int(parts[2])


def _build_response(bazi_r, wuxing_r, dayun_r, daily_r, reading,
                    yearly_r=None, yearly_reading=None) -> dict:
    pillars = bazi_r["pillars"]
    resp = {
        "bazi": {
            "pillars": pillars,
            "canggan": bazi_r["canggan"],
            "shishen": bazi_r["shishen"],
            "nayin": bazi_r["nayin"],
            "day_master": bazi_r["day_master"],
            "day_master_wuxing": bazi_r["day_master_wuxing"],
        },
        "wuxing": {
            "distribution": wuxing_r["distribution"],
            "day_master": wuxing_r["day_master"],
            "strength": wuxing_r["strength"],
            "favorable": wuxing_r["favorable"],
            "unfavorable": wuxing_r["unfavorable"],
            "missing": wuxing_r["missing"],
        },
        "dayun": {
            "start_age": dayun_r["start_age"],
            "current_dayun": dayun_r.get("current_dayun"),
            "current_liunian": dayun_r.get("current_liunian"),
            "list": dayun_r["list"],
        },
        "daily": daily_r,
        "reading": reading,
    }
    if yearly_r:
        resp["yearly"] = yearly_r
    if yearly_reading:
        resp["yearly_reading"] = yearly_reading
    return resp


def _get_lunar_month_days(year: int, month: int, is_leap: bool) -> int:
    try:
        from lunardate import LunarDate
        for day in (30, 29):
            try:
                LunarDate(year, month, day, isLeapMonth=is_leap)
                return day
            except ValueError:
                continue
    except ImportError:
        pass
    return 30


def _get_leap_month(year: int) -> int:
    try:
        from lunardate import LunarDate
        for m in range(1, 13):
            try:
                LunarDate(year, m, 1, isLeapMonth=True)
                return m
            except ValueError:
                continue
    except ImportError:
        pass
    return 0
