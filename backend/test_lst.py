from gee_service import get_lst_statistics


print("======================================")
print("TEST LST TP.HCM MỚI")
print("======================================")


result = get_lst_statistics(
    2026,
    1,
)


print(
    "Năm:",
    result["year"],
)

print(
    "Tháng:",
    result["month"],
)

print(
    "Số ảnh:",
    result["image_count"],
)

print(
    "LST thấp nhất:",
    result["lst_min_c"],
    "°C",
)

print(
    "LST trung bình:",
    result["lst_mean_c"],
    "°C",
)

print(
    "LST cao nhất:",
    result["lst_max_c"],
    "°C",
)


print("======================================")
print("TEST HOÀN TẤT")
print("======================================")