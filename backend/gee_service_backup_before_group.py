import json
from functools import lru_cache
from pathlib import Path

import ee

PROJECT_ID = "model-summit-509602-b1"
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
PROVINCES_FILE = DATA_DIR / "hcmc_provinces.json"
WARDS_FILE = DATA_DIR / "hcmc_wards.json"

# Thang tinh thong ke: van la du lieu LST that, chi khong tinh het 30 m khi
# lam thong ke tong hop. Ban do raster van giu nguyen do phan giai LST goc.
CITY_STATS_SCALE = 250
WARD_STATS_SCALE = 90
TIMESERIES_SCALE = 250


def _init_ee():
    try:
        ee.Initialize(project=PROJECT_ID)
    except Exception as exc:
        raise RuntimeError(
            f"Khong the khoi tao Google Earth Engine voi project {PROJECT_ID}: {exc}"
        ) from exc


_init_ee()


@lru_cache(maxsize=1)
def _load_provinces_data():
    if not PROVINCES_FILE.exists():
        raise FileNotFoundError(f"Thieu {PROVINCES_FILE}")
    with PROVINCES_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _load_wards_data():
    if not WARDS_FILE.exists():
        raise FileNotFoundError(f"Thieu {WARDS_FILE}")
    with WARDS_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def _find_hcmc_province():
    data = _load_provinces_data()
    provinces = data.get("provinces", data if isinstance(data, list) else [])
    for item in provinces:
        item_id = str(item.get("id", ""))
        name = str(item.get("name", ""))
        if item_id == "79" or "Hồ Chí Minh" in name or "Ho Chi Minh" in name:
            return item
    raise RuntimeError("Khong tim thay TP. Ho Chi Minh trong du lieu ranh gioi")


def _rings_to_ee_geometry(polygons):
    if not polygons:
        raise ValueError("Geometry rong")
    cleaned = []
    for ring in polygons:
        if not ring or len(ring) < 3:
            continue
        coords = [[float(p[0]), float(p[1])] for p in ring if len(p) >= 2]
        if len(coords) >= 3:
            if coords[0] != coords[-1]:
                coords.append(coords[0])
            cleaned.append([coords])
    if not cleaned:
        raise ValueError("Khong tao duoc polygon hop le")
    return ee.Geometry.MultiPolygon(cleaned, None, False)


@lru_cache(maxsize=1)
def _province_geometry():
    return _rings_to_ee_geometry(_find_hcmc_province()["polygons"])


@lru_cache(maxsize=1)
def _ward_items():
    return tuple(_load_wards_data().get("wards", []))


def _find_ward(area_code):
    code = str(area_code or "").strip()
    if not code:
        raise ValueError("Thieu ma phuong/xa")
    for ward in _ward_items():
        if str(ward.get("id", "")) == code:
            return ward
    raise ValueError(f"Khong tim thay don vi cap xa co ma {code}")


def _level_geometry(level="city", area_code=None):
    if level == "city":
        return _province_geometry()
    if level == "ward":
        return _rings_to_ee_geometry(_find_ward(area_code)["polygons"])
    raise ValueError("level phai la city hoac ward")


def get_areas():
    areas = []
    for ward in _ward_items():
        center = ward.get("center") or [None, None]
        areas.append({
            "code": str(ward.get("id", "")),
            "name": str(ward.get("name", "")),
            "type": str(ward.get("type", "")),
            "center": center,
        })
    return sorted(areas, key=lambda x: x["name"].lower())


def _ward_feature(ward):
    return ee.Feature(
        _rings_to_ee_geometry(ward["polygons"]),
        {
            "code": str(ward.get("id", "")),
            "name": str(ward.get("name", "")),
            "type": str(ward.get("type", "")),
        },
    )


def get_ward_feature_collection():
    return ee.FeatureCollection([_ward_feature(w) for w in _ward_items()])


def mask_landsat(image):
    qa_pixel = image.select("QA_PIXEL")
    qa_radsat = image.select("QA_RADSAT")
    clear_bits = (
        qa_pixel.bitwiseAnd(1 << 0).eq(0)
        .And(qa_pixel.bitwiseAnd(1 << 1).eq(0))
        .And(qa_pixel.bitwiseAnd(1 << 2).eq(0))
        .And(qa_pixel.bitwiseAnd(1 << 3).eq(0))
        .And(qa_pixel.bitwiseAnd(1 << 4).eq(0))
        .And(qa_pixel.bitwiseAnd(1 << 5).eq(0))
    )
    return image.updateMask(clear_bits).updateMask(qa_radsat.eq(0))


def convert_lst(image):
    lst_c = image.select("ST_B10").multiply(0.00341802).add(149.0).subtract(273.15)
    return image.addBands(lst_c.rename("LST_C"))


@lru_cache(maxsize=48)
def get_month_collection(year, month):
    """Tao collection theo thang 1 lan va dung lai cho city/ward/map/stats."""
    year = int(year)
    month = int(month)
    start = ee.Date.fromYMD(year, month, 1)
    end = start.advance(1, "month")

    def build(collection_id):
        return (
            ee.ImageCollection(collection_id)
            .filterBounds(_province_geometry())
            .filterDate(start, end)
            .map(mask_landsat)
            .map(convert_lst)
        )

    return build("LANDSAT/LC08/C02/T1_L2").merge(
        build("LANDSAT/LC09/C02/T1_L2")
    )


@lru_cache(maxsize=48)
def get_monthly_lst_city(year, month):
    year = int(year)
    month = int(month)
    return get_month_collection(year, month).select("LST_C").mean()


def get_monthly_lst(year, month, level="city", area_code=None):
    image = get_monthly_lst_city(int(year), int(month))
    aoi = _level_geometry(level, area_code)
    return image.clip(aoi)


@lru_cache(maxsize=96)
def get_month_image_count(year, month):
    return int(get_month_collection(int(year), int(month)).size().getInfo())


@lru_cache(maxsize=128)
def _stats_for_geometry(year, month, level, area_code):
    year = int(year)
    month = int(month)
    aoi = _level_geometry(level, area_code if level == "ward" else None)
    image = get_monthly_lst_city(year, month)
    scale = CITY_STATS_SCALE if level == "city" else WARD_STATS_SCALE
    stats = image.reduceRegion(
        reducer=ee.Reducer.minMax().combine(
            reducer2=ee.Reducer.mean(), sharedInputs=True
        ),
        geometry=aoi,
        scale=scale,
        bestEffort=True,
        maxPixels=1e8,
        tileScale=4,
    ).getInfo() or {}
    return {
        "year": year,
        "month": month,
        "image_count": get_month_image_count(year, month),
        "lst_min_c": stats.get("LST_C_min"),
        "lst_mean_c": stats.get("LST_C_mean"),
        "lst_max_c": stats.get("LST_C_max"),
    }


def get_lst_statistics(year, month, level="city", area_code=None):
    return _stats_for_geometry(
        int(year), int(month), level, str(area_code or "") if level == "ward" else ""
    )


def get_area_statistics(year, month, level="city", area_code=None):
    if level == "ward" and not area_code:
        raise ValueError("Phai chon phuong/xa")
    return get_lst_statistics(year, month, level, area_code)


def _timeseries_month(year, month, aoi):
    image = get_monthly_lst_city(year, month)
    value = image.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=aoi,
        scale=TIMESERIES_SCALE,
        bestEffort=True,
        maxPixels=1e8,
        tileScale=4,
    ).get("LST_C")
    return ee.Feature(
        None,
        {
            "date": ee.Date.fromYMD(year, month, 1).format("YYYY-MM"),
            "year": year,
            "month": month,
            "lst_mean_c": value,
        },
    )


@lru_cache(maxsize=48)
def get_area_timeseries(level="city", area_code=None, start_year=2017, end_year=2026):
    level = str(level)
    area_code = str(area_code or "")
    start_year = int(start_year)
    end_year = int(end_year)
    aoi = _level_geometry(level, area_code if level == "ward" else None)

    features = []
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            features.append(_timeseries_month(year, month, aoi))

    rows = ee.FeatureCollection(features).getInfo().get("features", [])
    result = [row.get("properties", {}) for row in rows]
    result.sort(key=lambda x: x.get("date", ""))
    return result


@lru_cache(maxsize=64)
def get_lst_at_point(latitude, longitude, year, month):
    point = ee.Geometry.Point([float(longitude), float(latitude)])
    image = get_monthly_lst_city(int(year), int(month))
    result = image.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=point,
        scale=30,
        bestEffort=True,
        maxPixels=1e7,
    ).getInfo() or {}
    return {
        "year": int(year),
        "month": int(month),
        "latitude": float(latitude),
        "longitude": float(longitude),
        "lst_c": result.get("LST_C"),
    }


@lru_cache(maxsize=4)
def get_boundary_geojson(level="city"):
    province = _find_hcmc_province()

    def rings_to_coordinates(polygons):
        coordinates = []
        for ring in polygons:
            if len(ring) >= 3:
                closed = [list(p) for p in ring]
                if closed[0] != closed[-1]:
                    closed.append(closed[0])
                coordinates.append([closed])
        return coordinates

    if level == "city":
        return {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "id": "79",
                "properties": {"code": "79", "name": "TP. Hồ Chí Minh", "type": "Thành phố"},
                "geometry": {"type": "MultiPolygon", "coordinates": rings_to_coordinates(province.get("polygons", []))},
            }],
        }

    if level == "ward":
        features = []
        for ward in _ward_items():
            features.append({
                "type": "Feature",
                "id": str(ward.get("id", "")),
                "properties": {
                    "code": str(ward.get("id", "")),
                    "name": str(ward.get("name", "")),
                    "type": str(ward.get("type", "")),
                },
                "geometry": {"type": "MultiPolygon", "coordinates": rings_to_coordinates(ward.get("polygons", []))},
            })
        return {"type": "FeatureCollection", "features": features}

    raise ValueError("level phai la city hoac ward")


@lru_cache(maxsize=96)
def get_map_info(year, month, level="city", area_code=None):
    image = get_monthly_lst(year, month, level, area_code)
    map_id = image.getMapId({
        "min": 20,
        "max": 50,
        "palette": [
            "040274", "2c7bb6", "00a6ca", "00ccbc", "90eb9d",
            "ffff8c", "f9d057", "f29e2e", "e76818", "d7191c",
        ],
    })
    return map_id
