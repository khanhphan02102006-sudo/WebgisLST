# ============================================================
# sync_statistics.py
#
# Google Earth Engine
#        ↓
# LST Statistics
#        ↓
# PostgreSQL
#
# Driver: pg8000
# ============================================================

import getpass
from datetime import date

import pg8000.dbapi

from gee_service import get_lst_statistics


# ============================================================
# 1. CẤU HÌNH POSTGRESQL
# ============================================================

DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "lst_webgis"
DB_USER = "postgres"


# ============================================================
# 2. NHẬP PASSWORD
# ============================================================

DB_PASSWORD = getpass.getpass(
    "Nhap password PostgreSQL: "
)


# ============================================================
# 3. KẾT NỐI DATABASE
# ============================================================

connection = pg8000.dbapi.connect(

    host=DB_HOST,

    port=DB_PORT,

    database=DB_NAME,

    user=DB_USER,

    password=DB_PASSWORD,

)

cursor = connection.cursor()


print()
print("========================================")
print("KẾT NỐI POSTGRESQL THÀNH CÔNG")
print("========================================")


# ============================================================
# 4. ĐỒNG BỘ 2017 → 2026
#    THÁNG 1
# ============================================================

for year in range(2017, 2027):

    month = 1

    print()
    print(
        f"Đang xử lý {year}-{month:02d}..."
    )

    try:

        # ----------------------------------------------------
        # Gọi GEE
        # ----------------------------------------------------

        result = get_lst_statistics(
            year,
            month,
        )


        # ----------------------------------------------------
        # Lấy kết quả
        # ----------------------------------------------------

        image_count = result[
            "image_count"
        ]

        lst_min = result[
            "lst_min_c"
        ]

        lst_mean = result[
            "lst_mean_c"
        ]

        lst_max = result[
            "lst_max_c"
        ]


        # ----------------------------------------------------
        # Ngày đại diện
        # ----------------------------------------------------

        obs_date = date(
            year,
            month,
            1,
        )


        # ----------------------------------------------------
        # INSERT / UPDATE
        # ----------------------------------------------------

        sql = """
        INSERT INTO lst_statistics (
            obs_date,
            year,
            month,
            image_count,
            lst_min_c,
            lst_mean_c,
            lst_max_c
        )
        VALUES (
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s
        )
        ON CONFLICT (year, month)
        DO UPDATE SET
            obs_date = EXCLUDED.obs_date,
            image_count = EXCLUDED.image_count,
            lst_min_c = EXCLUDED.lst_min_c,
            lst_mean_c = EXCLUDED.lst_mean_c,
            lst_max_c = EXCLUDED.lst_max_c,
            created_at = CURRENT_TIMESTAMP
        """


        cursor.execute(

            sql,

            (
                obs_date,
                year,
                month,
                image_count,
                lst_min,
                lst_mean,
                lst_max,
            )

        )


        connection.commit()


        # ----------------------------------------------------
        # Hiển thị
        # ----------------------------------------------------

        print(
            f"  Số ảnh : {image_count}"
        )

        print(
            f"  Min    : {lst_min} °C"
        )

        print(
            f"  Mean   : {lst_mean} °C"
        )

        print(
            f"  Max    : {lst_max} °C"
        )

        print(
            "  ✅ Đã lưu database"
        )


    except Exception as error:

        connection.rollback()

        print(
            f"  ❌ Lỗi năm {year}: {error}"
        )


# ============================================================
# 5. ĐÓNG DATABASE
# ============================================================

cursor.close()

connection.close()


print()
print("========================================")
print("HOÀN TẤT ĐỒNG BỘ GEE → POSTGRESQL")
print("========================================")