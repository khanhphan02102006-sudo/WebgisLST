import os
from pathlib import Path

import pg8000.dbapi
from dotenv import load_dotenv


# =========================================================
# ĐỌC FILE .ENV
# =========================================================

ENV_FILE = (
    Path(__file__)
    .resolve()
    .parents[1]
    / ".env"
)

load_dotenv(ENV_FILE)


# =========================================================
# KẾT NỐI POSTGRESQL
# =========================================================

def get_connection():

    host = os.getenv(
        "DB_HOST",
        "localhost"
    )

    port = int(
        os.getenv(
            "DB_PORT",
            "5432"
        )
    )

    database = os.getenv(
        "DB_NAME",
        "lst_webgis"
    )

    user = os.getenv(
        "DB_USER",
        "postgres"
    )

    password = os.getenv(
        "DB_PASSWORD"
    )

    if not password:

        raise RuntimeError(
            "Chưa cấu hình DB_PASSWORD "
            "trong file .env"
        )

    return pg8000.dbapi.connect(
        host=host,
        port=port,
        database=database,
        user=user,
        password=password
    )


# =========================================================
# TEST DATABASE
# =========================================================

def test_connection():

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute(
            "SELECT version();"
        )

        row = cursor.fetchone()

        cursor.close()

        return row[0]

    finally:

        connection.close()


# =========================================================
# LẤY STATISTICS 1 NĂM + 1 THÁNG
# =========================================================

def get_statistics(
    year=None,
    month=None
):

    connection = get_connection()

    try:

        cursor = connection.cursor()

        # -------------------------------------------------
        # Một tháng cụ thể
        # -------------------------------------------------

        if (
            year is not None
            and month is not None
        ):

            cursor.execute(
                """
                SELECT
                    year,
                    month,
                    image_count,
                    lst_min_c,
                    lst_mean_c,
                    lst_max_c
                FROM lst_statistics
                WHERE year = %s
                  AND month = %s
                LIMIT 1
                """,
                (
                    year,
                    month
                )
            )

            row = cursor.fetchone()

            if row is None:

                return None

            return {
                "year": row[0],
                "month": row[1],
                "image_count": row[2],
                "lst_min_c": row[3],
                "lst_mean_c": row[4],
                "lst_max_c": row[5],
            }

        # -------------------------------------------------
        # Toàn bộ statistics
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT
                year,
                month,
                image_count,
                lst_min_c,
                lst_mean_c,
                lst_max_c
            FROM lst_statistics
            ORDER BY
                year,
                month
            """
        )

        rows = cursor.fetchall()

        return [
            {
                "year": row[0],
                "month": row[1],
                "image_count": row[2],
                "lst_min_c": row[3],
                "lst_mean_c": row[4],
                "lst_max_c": row[5],
            }
            for row in rows
        ]

    finally:

        cursor.close()
        connection.close()


# =========================================================
# TIMESERIES TOÀN VÙNG
# =========================================================

def get_timeseries(
    month: int
):

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                year,
                month,
                image_count,
                lst_min_c,
                lst_mean_c,
                lst_max_c
            FROM lst_statistics
            WHERE month = %s
            ORDER BY year
            """,
            (
                month,
            )
        )

        rows = cursor.fetchall()

        return [
            {
                "year": row[0],
                "month": row[1],
                "image_count": row[2],
                "lst_min_c": row[3],
                "lst_mean_c": row[4],
                "lst_max_c": row[5],
            }
            for row in rows
        ]

    finally:

        cursor.close()
        connection.close()


# =========================================================
# LƯU TIMESERIES CỦA MỘT ĐIỂM
# =========================================================

def save_point_timeseries(
    month: int,
    lat: float,
    lon: float,
    data: list
):
    """
    Lưu chuỗi LST của một điểm vào lst_points.

    data có dạng:

    [
        {
            "year": 2017,
            "month": 1,
            "lst_c": 29.5,
            "image_count": 10
        },
        ...
    ]
    """

    connection = get_connection()

    try:

        cursor = connection.cursor()

        # -------------------------------------------------
        # Xóa dữ liệu cũ của cùng điểm + cùng tháng
        #
        # Dùng khoảng sai số rất nhỏ cho tọa độ.
        # -------------------------------------------------

        cursor.execute(
            """
            DELETE FROM lst_points
            WHERE month = %s
              AND ABS(latitude - %s) < 0.000001
              AND ABS(longitude - %s) < 0.000001
            """,
            (
                month,
                lat,
                lon
            )
        )

        # -------------------------------------------------
        # Insert dữ liệu mới
        # -------------------------------------------------

        inserted = 0

        for item in data:

            year = item.get(
                "year"
            )

            item_month = item.get(
                "month",
                month
            )

            lst_c = item.get(
                "lst_c"
            )

            # Nếu không có LST thì vẫn lưu
            # vị trí + thời gian, lst_c = NULL.
            cursor.execute(
                """
                INSERT INTO lst_points
                (
                    obs_date,
                    year,
                    month,
                    latitude,
                    longitude,
                    lst_c,
                    geometry
                )
                VALUES
                (
                    MAKE_DATE(%s, %s, 1),
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    ST_SetSRID(
                        ST_MakePoint(
                            %s,
                            %s
                        ),
                        4326
                    )
                )
                """,
                (
                    year,
                    item_month,
                    year,
                    item_month,
                    lat,
                    lon,
                    lst_c,
                    lon,
                    lat
                )
            )

            inserted += 1

        connection.commit()

        return {
            "success": True,
            "inserted": inserted,
            "latitude": lat,
            "longitude": lon,
            "month": month
        }

    except Exception:

        connection.rollback()

        raise

    finally:

        cursor.close()
        connection.close()


# =========================================================
# ĐỌC TIMESERIES CỦA MỘT ĐIỂM
# =========================================================

def get_point_timeseries(
    month: int,
    lat: float,
    lon: float
):

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                year,
                month,
                latitude,
                longitude,
                lst_c
            FROM lst_points
            WHERE month = %s
              AND ABS(latitude - %s) < 0.000001
              AND ABS(longitude - %s) < 0.000001
            ORDER BY year
            """,
            (
                month,
                lat,
                lon
            )
        )

        rows = cursor.fetchall()

        return [
            {
                "year": row[0],
                "month": row[1],
                "latitude": row[2],
                "longitude": row[3],
                "lst_c": row[4],
            }
            for row in rows
        ]

    finally:

        cursor.close()
        connection.close()


# =========================================================
# ĐẾM DỮ LIỆU POINT
# =========================================================

def count_points():

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM lst_points
            """
        )

        row = cursor.fetchone()

        return row[0]

    finally:

        cursor.close()
        connection.close()