"""FastAPI backend của WebGIS LST TP.HCM."""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

import db_service
import gee_service

app = FastAPI(
    title="WebGIS LST TP.HCM",
    version="2.1",
    description="WebGIS LST theo TP.HCM mới và các đơn vị cấp xã hiện hành.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _level(level: str) -> str:
    level = (level or "city").strip().lower()
    mapping = {
        "city": "city",
        "hcmc": "city",
        "ward": "ward",
        "phuong": "ward",
        "xa": "ward",
    }
    if level not in mapping:
        raise HTTPException(status_code=400, detail="level phải là city hoặc ward")
    return mapping[level]


@app.get("/api")
def root():
    return {
        "name": "WebGIS LST TP.HCM",
        "boundary": "TP.HCM mới",
        "levels": ["city", "ward"],
        "note": "Polygon và LST dùng đơn vị hành chính hiện hành của TP.HCM.",
    }


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/info")
def info():
    return {
        "project": gee_service.PROJECT_ID,
        "study_area": "TP. Hồ Chí Minh",
        "administrative_model": "2 cấp",
        "ward_count": len(gee_service.get_areas()),
        "years": [2017, 2026],
    }


@app.get("/api/area-groups")
def area_groups():
    """Danh sách nhóm khu vực tham chiếu cho bộ lọc frontend."""
    return gee_service.get_area_groups()


@app.get("/api/areas")
def areas(level: str = "ward", group: str | None = None):
    level = _level(level)
    if level == "city":
        return [{"code": "79", "name": "TP. Hồ Chí Minh", "type": "Thành phố", "group": "Toàn TP.HCM"}]

    items = gee_service.get_areas()
    if not group or group in {"ALL", ""}:
        return items
    if group == "OTHER":
        return [x for x in items if x["group"] == "Khác - TP.HCM mới"]
    return [x for x in items if x["group"] == group]


@app.get("/api/boundary")
def boundary(level: str = "city"):
    try:
        return gee_service.get_boundary_geojson(_level(level))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/lst")
def lst(
    year: int = Query(..., ge=2017, le=2026),
    month: int = Query(..., ge=1, le=12),
    level: str = "city",
    area_code: str | None = None,
):
    try:
        level = _level(level)
        stats = gee_service.get_area_statistics(year, month, level, area_code)
        map_info = gee_service.get_map_info(year, month, level, area_code)
        return {
            "year": year,
            "month": month,
            "level": level,
            "area_code": area_code,
            "statistics": stats,
            "map": {
                "mapid": map_info["mapid"],
                "token": map_info["token"],
                "tile_url": map_info["tile_fetcher"].url_format,
            },
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/map")
def map_layer(
    year: int = Query(..., ge=2017, le=2026),
    month: int = Query(..., ge=1, le=12),
    level: str = "city",
    area_code: str | None = None,
):
    try:
        info = gee_service.get_map_info(year, month, _level(level), area_code)
        return {"tile_url": info["tile_fetcher"].url_format}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/area-statistics")
def area_statistics(
    year: int = Query(..., ge=2017, le=2026),
    month: int = Query(..., ge=1, le=12),
    level: str = "city",
    area_code: str | None = None,
):
    try:
        return gee_service.get_area_statistics(year, month, _level(level), area_code)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/ward-statistics")
def ward_statistics(
    year: int = Query(..., ge=2017, le=2026),
    month: int = Query(..., ge=1, le=12),
):
    """Một request GEE cho toàn bộ phường/xã để hover nhanh."""
    try:
        return gee_service.get_ward_statistics_bulk(year, month)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/area-timeseries")
def area_timeseries(
    level: str = "city",
    area_code: str | None = None,
    start_year: int = Query(2017, ge=2017, le=2026),
    end_year: int = Query(2026, ge=2017, le=2026),
):
    if end_year < start_year:
        raise HTTPException(status_code=400, detail="end_year phải lớn hơn hoặc bằng start_year")
    try:
        return gee_service.get_area_timeseries(_level(level), area_code, start_year, end_year)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# API cũ giữ lại để không phá frontend/code cũ nếu đang có nơi gọi.
@app.get("/api/province-statistics")
def province_statistics(
    year: int = Query(..., ge=2017, le=2026),
    month: int = Query(..., ge=1, le=12),
    level: str = "city",
    area_code: str | None = None,
):
    return area_statistics(year, month, level, area_code)


@app.get("/api/province-timeseries")
def province_timeseries(level: str = "city", area_code: str | None = None):
    return area_timeseries(level, area_code, 2017, 2026)


@app.get("/api/lst-point")
def lst_point(
    latitude: float,
    longitude: float,
    year: int = Query(..., ge=2017, le=2026),
    month: int = Query(..., ge=1, le=12),
):
    try:
        return gee_service.get_lst_at_point(latitude, longitude, year, month)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/timeseries")
def timeseries(level: str = "city", area_code: str | None = None):
    return area_timeseries(level, area_code, 2017, 2026)


@app.get("/api/db/statistics")
def db_statistics():
    try:
        return db_service.get_statistics()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
