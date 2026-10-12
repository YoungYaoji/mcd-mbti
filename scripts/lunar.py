"""农历转换（1900-2099），纯标准库实现。

算法来源：经典 lunarInfo 位压缩表（公共领域算法），
每年一个十六进制数：低 4 位为闰月月份，0 表示无闰月；
第 16 位表示闰月大小（1=大月30天）；第 15-4 位依次表示 1-12 月大小（1=30天）。
基准日：1900-01-31 为农历庚子年正月初一。
数据：经典 lunarInfo 位压缩编码（与 lunardate 等开源实现的编码一致）。
"""

from __future__ import annotations

import datetime as dt

LUNAR_INFO = [
    0x04bd8, 0x04ae0, 0x0a570, 0x054d5, 0x0d260, 0x0d950, 0x16554, 0x056a0, 0x09ad0, 0x055d2,
    0x04ae0, 0x0a5b6, 0x0a4d0, 0x0d250, 0x1d255, 0x0b540, 0x0d6a0, 0x0ada2, 0x095b0, 0x14977,
    0x04970, 0x0a4b0, 0x0b4b5, 0x06a50, 0x06d40, 0x1ab54, 0x02b60, 0x09570, 0x052f2, 0x04970,
    0x06566, 0x0d4a0, 0x0ea50, 0x06e95, 0x05ad0, 0x02b60, 0x186e3, 0x092e0, 0x1c8d7, 0x0c950,
    0x0d4a0, 0x1d8a6, 0x0b550, 0x056a0, 0x1a5b4, 0x025d0, 0x092d0, 0x0d2b2, 0x0a950, 0x0b557,
    0x06ca0, 0x0b550, 0x15355, 0x04da0, 0x0a5d0, 0x14573, 0x052b0, 0x0a9a8, 0x0e950, 0x06aa0,
    0x0aea6, 0x0ab50, 0x04b60, 0x0aae4, 0x0a570, 0x05260, 0x0f263, 0x0d950, 0x05b57, 0x056a0,
    0x096d0, 0x04dd5, 0x04ad0, 0x0a4d0, 0x0d4d4, 0x0d250, 0x0d558, 0x0b540, 0x0b5a0, 0x195a6,
    0x095b0, 0x049b0, 0x0a974, 0x0a4b0, 0x0b27a, 0x06a50, 0x06d40, 0x0af46, 0x0ab60, 0x09570,
    0x04af5, 0x04970, 0x064b0, 0x074a3, 0x0ea50, 0x06b58, 0x05ac0, 0x0ab60, 0x096d5, 0x092e0,
    0x0c960, 0x0d954, 0x0d4a0, 0x0da50, 0x07552, 0x056a0, 0x0abb7, 0x025d0, 0x092d0, 0x0cab5,
    0x0a950, 0x0b4a0, 0x0baa4, 0x0ad50, 0x055d9, 0x04ba0, 0x0a5b0, 0x15176, 0x052b0, 0x0a930,
    0x07954, 0x06aa0, 0x0ad50, 0x05b52, 0x04b60, 0x0a6e6, 0x0a4e0, 0x0d260, 0x0ea65, 0x0d530,
    0x05aa0, 0x076a3, 0x096d0, 0x04afb, 0x04ad0, 0x0a4d0, 0x1d0b6, 0x0d250, 0x0d520, 0x0dd45,
    0x0b5a0, 0x056d0, 0x055b2, 0x049b0, 0x0a577, 0x0a4b0, 0x0aa50, 0x1b255, 0x06d20, 0x0ada0,
    0x14b63, 0x09370, 0x049f8, 0x04970, 0x064b0, 0x168a6, 0x0ea50, 0x06aa0, 0x1a6c4, 0x0aae0,
    0x092e0, 0x0d2e3, 0x0c960, 0x0d557, 0x0d4a0, 0x0da50, 0x05d55, 0x056a0, 0x0a6d0, 0x055d4,
    0x052d0, 0x0a9b8, 0x0a950, 0x0b4a0, 0x0b6a6, 0x0ad50, 0x055a0, 0x0aba4, 0x0a5b0, 0x052b0,
    0x0b273, 0x06930, 0x07337, 0x06aa0, 0x0ad50, 0x14b55, 0x04b60, 0x0a570, 0x054e4, 0x0d160,
    0x0e968, 0x0d520, 0x0daa0, 0x16aa6, 0x056d0, 0x04ae0, 0x0a9d4, 0x0a2d0, 0x0d150, 0x0f252,
]

TIANGAN = "甲乙丙丁戊己庚辛壬癸"
DIZHI = "子丑寅卯辰巳午未申酉戌亥"
SHENGXIAO = "鼠牛虎兔龙蛇马羊猴鸡狗猪"
LUNAR_MONTHS = "正二三四五六七八九十冬腊"
LUNAR_DAYS = (
    "初一 初二 初三 初四 初五 初六 初七 初八 初九 初十 "
    "十一 十二 十三 十四 十五 十六 十七 十八 十九 二十 "
    "廿一 廿二 廿三 廿四 廿五 廿六 廿七 廿八 廿九 三十"
).split()

WEEKDAYS = "一二三四五六日"

BASE_DATE = dt.date(1900, 1, 31)  # 农历 1900 年正月初一


def _leap_month(year: int) -> int:
    return LUNAR_INFO[year - 1900] & 0xF


def _leap_days(year: int) -> int:
    if _leap_month(year):
        return 30 if (LUNAR_INFO[year - 1900] & 0x10000) else 29
    return 0


def _month_days(year: int, month: int) -> int:
    return 30 if (LUNAR_INFO[year - 1900] & (0x10000 >> month)) else 29


def _year_days(year: int) -> int:
    total = 348  # 12 * 29
    info = LUNAR_INFO[year - 1900]
    for m in range(1, 13):
        if info & (0x10000 >> m):
            total += 1
    return total + _leap_days(year)


def solar_to_lunar(date: dt.date) -> dict:
    """公历 -> 农历。返回 {year, month, day, is_leap, month_cn, day_cn, year_cn}。"""
    if not (dt.date(1900, 1, 31) <= date <= dt.date(2099, 12, 31)):
        raise ValueError(f"日期超出支持范围（1900-01-31 ~ 2099-12-31）：{date}")

    offset = (date - BASE_DATE).days
    year = 1900
    while offset >= _year_days(year):
        offset -= _year_days(year)
        year += 1

    # 按“年内的月份序列”逐月扣减，闰月插在正常月份之后
    leap = _leap_month(year)
    months: list[tuple[int, int, bool]] = []
    for m in range(1, 13):
        months.append((m, _month_days(year, m), False))
        if m == leap:
            months.append((m, _leap_days(year), True))

    month, day, is_leap = 1, 1, False
    for m, month_days, leap_flag in months:
        if offset < month_days:
            month, day, is_leap = m, offset + 1, leap_flag
            break
        offset -= month_days

    gan_index = (year - 4) % 10
    zhi_index = (year - 4) % 12
    month_cn = ("闰" if is_leap else "") + LUNAR_MONTHS[month - 1] + "月"
    return {
        "year": year,
        "month": month,
        "day": day,
        "is_leap": is_leap,
        "month_cn": month_cn,
        "day_cn": LUNAR_DAYS[day - 1],
        "year_cn": f"{TIANGAN[gan_index]}{DIZHI[zhi_index]}年",
        "shengxiao": SHENGXIAO[zhi_index],
    }


def day_of_year(date: dt.date) -> int:
    return (date - dt.date(date.year, 1, 1)).days + 1


def _self_check() -> None:
    """用已知节日锚点校验转换表。"""
    anchors = [
        (dt.date(2025, 1, 29), "正月初一", False),    # 2025 春节
        (dt.date(2025, 5, 31), "五月初五", False),    # 2025 端午
        (dt.date(2025, 10, 6), "八月十五", False),    # 2025 中秋
        (dt.date(2026, 2, 17), "正月初一", False),    # 2026 春节
        (dt.date(2026, 6, 19), "五月初五", False),    # 2026 端午
        (dt.date(2026, 9, 25), "八月十五", False),    # 2026 中秋
    ]
    for date, expect, is_leap in anchors:
        got = solar_to_lunar(date)
        actual = f"{got['month_cn'].replace('闰', '')}{got['day_cn']}"
        assert actual == expect and got["is_leap"] == is_leap, f"{date} 期望 {expect}，实际 {actual}"
    # 2025 年有闰六月
    rl = solar_to_lunar(dt.date(2025, 8, 1))
    assert rl["is_leap"] and rl["month"] == 6, f"2025-08-01 应为闰六月，实际 {rl}"


if __name__ == "__main__":
    _self_check()
    print("农历转换表自检通过。")
    today = dt.date.today()
    info = solar_to_lunar(today)
    print(f"{today} -> {info['year_cn']}{info['month_cn']}{info['day_cn']}（{info['shengxiao']}年）")
