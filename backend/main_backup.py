from fastapi import (
    FastAPI,
    Query,
    HTTPException
)

from fastapi.middleware.cors import (
    CORSMiddleware
)

import gee_service


app = FastAPI(
    title="LST WebGIS TP.HCM Mới",
    description=(
        "WebGIS LST sử dụng Google Earth Engine "
        "và PostgreSQL/PostGIS"
    ),
    version="1.2.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)


# =========================================================
# HOME
# =========================================================

@app.get("/")
def home():

    return {
        "success": True,
        "message": "LST WebGIS API đang hoạt động",
        "project": "TP.HCM mới",
        "source": "Google Earth Engine",
        "docs": "/docs"
    }


# =========================================================
# HEALTH
# =========================================================

@app.get("/api/health")
def health():

    return {
        "success": True,
        "status": "ok",
        "service": "LST WebGIS",
        "earth_engine": "connected",
        "database": "PostgreSQL"
    }


# =========================================================
# INFO
# =========================================================

@app.get("/api/info")
def info():

    return {
        "success": True,
        "name": "LST WebGIS TP.HCM mới",
        "data_source": "Google Earth Engine",
        "satellites": [
            "Landsat 8",
            "Landsat 9"
        ],
        "index": "LST - Land Surface Temperature",
        "region": "TP.HCM mới",
        "period": "2017-2026",
        "resolution": "30 m",
        "unit": "°C",
        "spatial_units": [
            "TP.HCM cũ",
            "Bình Dương cũ",
            "Bà Rịa - Vũng Tàu cũ"
        ]
    }


# =========================================================
# LST
# =========================================================

@app.get("/api/lst")
def get_lst(

    year: int = Query(
        2026,
        ge=2017,
        le=2026
    ),

    month: int = Query(
        1,
        ge=1,
        le=12
    )

):

    try:

        statistics = (
            gee_service
            .get_lst_statistics(
                year,
                month
            )
        )


        map_info = (
            gee_service
            .get_map_info(
                year,
                month
            )
        )


        tile_url = (
            map_info[
                "tile_fetcher"
            ]
            .url_format
        )


        return {

            "success":
                True,

            "region":
                "TP.HCM mới",

            "year":
                year,

            "month":
                month,

            "date":
                f"{year}-{month:02d}",

            "image_count":
                statistics[
                    "image_count"
                ],

            "lst_min_c":
                statistics[
                    "lst_min_c"
                ],

            "lst_mean_c":
                statistics[
                    "lst_mean_c"
                ],

            "lst_max_c":
                statistics[
                    "lst_max_c"
                ],

            "tile_url":
                tile_url,

            "attribution":
                "Google Earth Engine / Landsat 8/9"

        }


    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Lỗi lấy LST: {str(e)}"
        )


# =========================================================
# MAP
# =========================================================

@app.get("/api/map")
def get_map(

    year: int = Query(
        2026,
        ge=2017,
        le=2026
    ),

    month: int = Query(
        1,
        ge=1,
        le=12
    )

):

    try:

        map_info = (
            gee_service
            .get_map_info(
                year,
                month
            )
        )


        tile_url = (
            map_info[
                "tile_fetcher"
            ]
            .url_format
        )


        return {

            "success":
                True,

            "year":
                year,

            "month":
                month,

            "tile_url":
                tile_url

        }


    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Lỗi tạo bản đồ: {str(e)}"
        )


# =========================================================
# BOUNDARY
# =========================================================

@app.get("/api/boundary")
def get_boundary():

    try:

        return (
            gee_service
            .get_boundary_geojson()
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Lỗi lấy ranh giới: {str(e)}"
        )


# =========================================================
# THỐNG KÊ TỈNH
# =========================================================

@app.get("/api/province-statistics")
def province_statistics(

    year: int = Query(
        2026,
        ge=2017,
        le=2026
    ),

    month: int = Query(
        1,
        ge=1,
        le=12
    )

):

    try:

        data = (
            gee_service
            .get_province_statistics(
                year,
                month
            )
        )


        return {

            "success":
                True,

            "source":
                "Google Earth Engine",

            "year":
                year,

            "month":
                month,

            "data":
                data

        }


    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Lỗi thống kê tỉnh: {str(e)}"
        )


# =========================================================
# TIMESERIES TỈNH
# =========================================================

@app.get("/api/province-timeseries")
def province_timeseries(

    province: str = Query(...),

    month: int = Query(
        1,
        ge=1,
        le=12
    )

):

    try:

        data = (
            gee_service
            .get_province_timeseries(
                province,
                month
            )
        )


        return {

            "success":
                True,

            "source":
                "Google Earth Engine",

            "province":
                province,

            "month":
                month,

            "data":
                data

        }


    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Lỗi timeseries tỉnh: {str(e)}"
        )


# =========================================================
# LST POINT
# =========================================================

@app.get("/api/lst-point")
def lst_point(

    year: int = Query(
        2026,
        ge=2017,
        le=2026
    ),

    month: int = Query(
        1,
        ge=1,
        le=12
    ),

    lat: float = Query(
        ...,
        ge=-90,
        le=90
    ),

    lon: float = Query(
        ...,
        ge=-180,
        le=180
    )

):

    try:

        data = (
            gee_service
            .get_lst_at_point(
                year,
                month,
                lat,
                lon
            )
        )


        return {

            "success":
                True,

            "region":
                "TP.HCM mới",

            **data

        }


    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Lỗi LST tại điểm: {str(e)}"
        )


# =========================================================
# TIMESERIES ĐIỂM
# =========================================================

@app.get("/api/timeseries")
def timeseries(

    month: int = Query(
        1,
        ge=1,
        le=12
    ),

    lat: float = Query(
        ...,
        ge=-90,
        le=90
    ),

    lon: float = Query(
        ...,
        ge=-180,
        le=180
    )

):

    try:

        data = (
            gee_service
            .get_lst_timeseries(
                month,
                lat,
                lon
            )
        )


        return {

            "success":
                True,

            "source":
                "Google Earth Engine",

            "month":
                month,

            "latitude":
                lat,

            "longitude":
                lon,

            "data":
                data

        }


    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Lỗi timeseries điểm: {str(e)}"
        )


# =========================================================
# API LIST
# =========================================================

@app.get("/api")
def api_list():

    return {

        "success":
            True,

        "message":
            "LST WebGIS API",

        "endpoints": [

            "/",
            "/docs",
            "/api/health",
            "/api/info",
            "/api/lst",
            "/api/map",
            "/api/boundary",
            "/api/province-statistics",
            "/api/province-timeseries",
            "/api/lst-point",
            "/api/timeseries"

        ]

    }