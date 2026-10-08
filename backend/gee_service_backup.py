import ee
from functools import lru_cache


PROJECT_ID = "model-summit-509602-b1"

ee.Initialize(
    project=PROJECT_ID
)


# =========================================================
# RANH GIỚI
# =========================================================

GAUL = ee.FeatureCollection(
    "FAO/GAUL/2015/level1"
)


PROVINCE_NAMES = [
    "Ho Chi Minh City",
    "Binh Duong",
    "Ba Ria-Vung Tau",
]


PROVINCE_LABELS = {
    "Ho Chi Minh City": "TP.HCM cũ",
    "Binh Duong": "Bình Dương cũ",
    "Ba Ria-Vung Tau": "Bà Rịa - Vũng Tàu cũ",
}


AOI_FEATURES = GAUL.filter(
    ee.Filter.And(
        ee.Filter.eq(
            "ADM0_NAME",
            "Viet Nam"
        ),
        ee.Filter.inList(
            "ADM1_NAME",
            PROVINCE_NAMES
        ),
    )
)


AOI = AOI_FEATURES.geometry()


# =========================================================
# LANDSAT MASK
# =========================================================

def mask_landsat(image):

    qa = image.select(
        "QA_PIXEL"
    )


    mask = (
        qa.bitwiseAnd(1 << 0).eq(0)
        .And(
            qa.bitwiseAnd(1 << 1).eq(0)
        )
        .And(
            qa.bitwiseAnd(1 << 2).eq(0)
        )
        .And(
            qa.bitwiseAnd(1 << 3).eq(0)
        )
        .And(
            qa.bitwiseAnd(1 << 4).eq(0)
        )
        .And(
            qa.bitwiseAnd(1 << 5).eq(0)
        )
    )


    qa_radsat = image.select(
        "QA_RADSAT"
    )


    mask = mask.And(
        qa_radsat.eq(0)
    )


    return image.updateMask(
        mask
    )


# =========================================================
# LST
# =========================================================

def convert_lst(image):

    lst_c = (
        image
        .select("ST_B10")
        .multiply(0.00341802)
        .add(149.0)
        .subtract(273.15)
        .rename("LST_C")
    )


    return lst_c.copyProperties(
        image,
        image.propertyNames()
    )


# =========================================================
# LANDSAT 8
# =========================================================

def get_landsat8(
    start_date,
    end_date
):

    return (
        ee.ImageCollection(
            "LANDSAT/LC08/C02/T1_L2"
        )
        .filterDate(
            start_date,
            end_date
        )
        .filterBounds(
            AOI
        )
        .map(
            mask_landsat
        )
        .map(
            convert_lst
        )
    )


# =========================================================
# LANDSAT 9
# =========================================================

def get_landsat9(
    start_date,
    end_date
):

    return (
        ee.ImageCollection(
            "LANDSAT/LC09/C02/T1_L2"
        )
        .filterDate(
            start_date,
            end_date
        )
        .filterBounds(
            AOI
        )
        .map(
            mask_landsat
        )
        .map(
            convert_lst
        )
    )


# =========================================================
# COLLECTION THÁNG
# =========================================================

def get_month_collection(
    year,
    month
):

    start_date = (
        f"{year}-{month:02d}-01"
    )


    if month == 12:

        end_date = (
            f"{year + 1}-01-01"
        )

    else:

        end_date = (
            f"{year}-{month + 1:02d}-01"
        )


    collection8 = (
        get_landsat8(
            start_date,
            end_date
        )
    )


    collection9 = (
        get_landsat9(
            start_date,
            end_date
        )
    )


    return (
        collection8
        .merge(
            collection9
        )
        .filterBounds(
            AOI
        )
    )


# =========================================================
# LST THÁNG
# =========================================================

def get_monthly_lst(
    year,
    month
):

    collection = (
        get_month_collection(
            year,
            month
        )
    )


    image_count = (
        collection.size()
    )


    composite = (
        collection
        .median()
        .clip(AOI)
        .rename(
            "LST_C"
        )
    )


    return (
        composite,
        image_count
    )


# =========================================================
# THỐNG KÊ TOÀN VÙNG
# =========================================================

def get_lst_statistics(
    year,
    month
):

    collection = (
        get_month_collection(
            year,
            month
        )
    )


    image_count = (
        collection
        .size()
        .getInfo()
    )


    if image_count == 0:

        return {
            "year": year,
            "month": month,
            "image_count": 0,
            "lst_min_c": None,
            "lst_mean_c": None,
            "lst_max_c": None,
        }


    image = (
        collection
        .median()
        .clip(AOI)
    )


    reducer = (
        ee.Reducer.minMax()
        .combine(
            reducer2=
                ee.Reducer.mean(),
            sharedInputs=True
        )
    )


    stats = (
        image
        .reduceRegion(
            reducer=
                reducer,
            geometry=
                AOI,
            scale=30,
            maxPixels=1e13,
            bestEffort=True
        )
        .getInfo()
    )


    min_c = stats.get(
        "LST_C_min"
    )

    mean_c = stats.get(
        "LST_C_mean"
    )

    max_c = stats.get(
        "LST_C_max"
    )


    return {
        "year": year,
        "month": month,
        "image_count": image_count,
        "lst_min_c": (
            round(min_c, 2)
            if min_c is not None
            else None
        ),
        "lst_mean_c": (
            round(mean_c, 2)
            if mean_c is not None
            else None
        ),
        "lst_max_c": (
            round(max_c, 2)
            if max_c is not None
            else None
        ),
    }


# =========================================================
# GEOMETRY TỈNH
# =========================================================

def get_province_geometry(
    province_name
):

    if province_name not in PROVINCE_NAMES:

        raise ValueError(
            "Tên tỉnh/thành không hợp lệ."
        )


    return (
        AOI_FEATURES
        .filter(
            ee.Filter.eq(
                "ADM1_NAME",
                province_name
            )
        )
        .geometry()
    )


# =========================================================
# THỐNG KÊ TỈNH
# =========================================================

def get_province_statistics(
    year,
    month
):

    collection = (
        get_month_collection(
            year,
            month
        )
    )


    image_count = (
        collection
        .size()
        .getInfo()
    )


    if image_count == 0:

        return []


    image = (
        collection
        .median()
    )


    reducer = (
        ee.Reducer.minMax()
        .combine(
            reducer2=
                ee.Reducer.mean(),
            sharedInputs=True
        )
    )


    results = []


    for province_name in PROVINCE_NAMES:

        geometry = (
            get_province_geometry(
                province_name
            )
        )


        stats = (
            image
            .reduceRegion(
                reducer=
                    reducer,
                geometry=
                    geometry,
                scale=30,
                maxPixels=1e13,
                bestEffort=True
            )
            .getInfo()
        )


        results.append({

            "province":
                province_name,

            "province_label":
                PROVINCE_LABELS[
                    province_name
                ],

            "year":
                year,

            "month":
                month,

            "image_count":
                image_count,

            "lst_min_c":
                (
                    round(
                        stats[
                            "LST_C_min"
                        ],
                        2
                    )
                    if stats.get(
                        "LST_C_min"
                    ) is not None
                    else None
                ),

            "lst_mean_c":
                (
                    round(
                        stats[
                            "LST_C_mean"
                        ],
                        2
                    )
                    if stats.get(
                        "LST_C_mean"
                    ) is not None
                    else None
                ),

            "lst_max_c":
                (
                    round(
                        stats[
                            "LST_C_max"
                        ],
                        2
                    )
                    if stats.get(
                        "LST_C_max"
                    ) is not None
                    else None
                ),

        })


    return results


# =========================================================
# TIMESERIES TỈNH
# =========================================================

@lru_cache(
    maxsize=36
)
def get_province_timeseries(
    province_name,
    month
):

    geometry = (
        get_province_geometry(
            province_name
        )
    )


    results = []


    for year in range(
        2017,
        2027
    ):

        collection = (
            get_month_collection(
                year,
                month
            )
        )


        image_count = (
            collection
            .size()
            .getInfo()
        )


        if image_count == 0:

            results.append({

                "year":
                    year,

                "month":
                    month,

                "lst_c":
                    None,

                "image_count":
                    0

            })

            continue


        image = (
            collection
            .median()
        )


        stats = (
            image
            .reduceRegion(
                reducer=
                    ee.Reducer.mean(),

                geometry=
                    geometry,

                scale=30,

                maxPixels=1e13,

                bestEffort=True

            )
            .getInfo()
        )


        value = stats.get(
            "LST_C"
        )


        results.append({

            "year":
                year,

            "month":
                month,

            "lst_c":
                (
                    round(
                        value,
                        2
                    )
                    if value is not None
                    else None
                ),

            "image_count":
                image_count

        })


    return results


# =========================================================
# GEOJSON
# =========================================================

def get_boundary_geojson():

    data = (
        AOI_FEATURES
        .getInfo()
    )


    for feature in data.get(
        "features",
        []
    ):

        properties = feature.get(
            "properties",
            {}
        )


        name = properties.get(
            "ADM1_NAME"
        )


        properties[
            "display_name"
        ] = PROVINCE_LABELS.get(
            name,
            name
        )


    return {

        "type":
            "FeatureCollection",

        "features":
            data.get(
                "features",
                []
            )

    }


# =========================================================
# MAP
# =========================================================

@lru_cache(
    maxsize=24
)
def get_map_info(
    year,
    month
):

    lst_image, _ = (
        get_monthly_lst(
            year,
            month
        )
    )


    vis_params = {

        "min":
            20,

        "max":
            50,

        "palette": [

            "040274",
            "1B45A8",
            "2C7BB6",
            "00A6CA",
            "00CCBC",
            "90EB9D",
            "FFFF8C",
            "F9D057",
            "F29E2E",
            "E85D25",
            "C22E18",
            "7A0403"

        ]

    }


    return (
        lst_image
        .getMapId(
            vis_params
        )
    )


# =========================================================
# LST ĐIỂM
# =========================================================

def get_lst_at_point(
    year,
    month,
    lat,
    lon
):

    point = ee.Geometry.Point(
        [
            lon,
            lat
        ]
    )


    inside = (
        AOI
        .contains(
            point
        )
        .getInfo()
    )


    if not inside:

        return {

            "year":
                year,

            "month":
                month,

            "latitude":
                lat,

            "longitude":
                lon,

            "lst_c":
                None,

            "inside_region":
                False

        }


    collection = (
        get_month_collection(
            year,
            month
        )
    )


    count = (
        collection
        .size()
        .getInfo()
    )


    if count == 0:

        return {

            "year":
                year,

            "month":
                month,

            "latitude":
                lat,

            "longitude":
                lon,

            "lst_c":
                None,

            "inside_region":
                True,

            "image_count":
                0

        }


    image = (
        collection
        .median()
    )


    stats = (
        image
        .reduceRegion(
            reducer=
                ee.Reducer.first(),

            geometry=
                point,

            scale=30,

            maxPixels=1e6
        )
        .getInfo()
    )


    value = stats.get(
        "LST_C"
    )


    return {

        "year":
            year,

        "month":
            month,

        "latitude":
            lat,

        "longitude":
            lon,

        "lst_c":
            (
                round(
                    value,
                    2
                )
                if value is not None
                else None
            ),

        "image_count":
            count,

        "inside_region":
            True

    }


# =========================================================
# TIMESERIES ĐIỂM
# =========================================================

def get_lst_timeseries(
    month,
    lat,
    lon
):

    point = ee.Geometry.Point(
        [
            lon,
            lat
        ]
    )


    if not AOI.contains(
        point
    ).getInfo():

        return []


    results = []


    for year in range(
        2017,
        2027
    ):

        collection = (
            get_month_collection(
                year,
                month
            )
        )


        count = (
            collection
            .size()
            .getInfo()
        )


        if count == 0:

            results.append({

                "year":
                    year,

                "month":
                    month,

                "lst_c":
                    None,

                "image_count":
                    0

            })

            continue


        image = (
            collection
            .median()
        )


        stats = (
            image
            .reduceRegion(
                reducer=
                    ee.Reducer.first(),

                geometry=
                    point,

                scale=30,

                maxPixels=1e6
            )
            .getInfo()
        )


        value = stats.get(
            "LST_C"
        )


        results.append({

            "year":
                year,

            "month":
                month,

            "lst_c":
                (
                    round(
                        value,
                        2
                    )
                    if value is not None
                    else None
                ),

            "image_count":
                count

        })


    return results