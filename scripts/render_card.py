"""麦门人格鉴定所 · 人格鉴定卡 SVG 渲染器。

风格：现代心理测评卡（麦当劳红黄配色 + 米白纸面），
结构：人格代号大字 → 四轴天平 → 麦门成分 → 行为分析 → 相处指南。
动态测量布局，内容多少自动决定卡片高度。
"""

from __future__ import annotations

from xml.sax.saxutils import escape

# 配色（麦当劳品牌色系）
RED = "#DA291C"
DARK_RED = "#A4161A"
YELLOW = "#FFC72C"
CREAM = "#FFF8E8"
PAPER = "#FFFDF6"
INK = "#27251F"
GREY = "#8A8378"
GREEN = "#2E7D4F"
BLUE = "#3D5A99"

FONT = "'Noto Sans SC','PingFang SC','Microsoft YaHei','Source Han Sans SC',sans-serif"

AXIS_META = {
    "EI": ("社交能量", "E", "I", RED, BLUE),
    "SN": ("点单风格", "S", "N", GREEN, "#B5651D"),
    "TF": ("消费决策", "T", "F", "#5B4FA8", "#C2185B"),
    "JP": ("时间节律", "J", "P", "#00695C", "#E65100"),
}


def _t(x: float, y: float, size: float, fill: str, content: str, anchor: str = "start",
       weight: str = "400", spacing: float | None = None) -> str:
    ls = f' letter-spacing="{spacing}"' if spacing else ""
    return (
        f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" '
        f'font-family="{FONT}" font-weight="{weight}"{ls}>{escape(content)}</text>'
    )


def build_svg(persona: dict, width: int = 680) -> str:
    code = persona["code"]
    letters = persona["letters"]
    scores = persona["axis_scores"]
    stats = persona["stats"]
    ing = persona["ingredients"]
    notes = persona["notes"]

    # ---------------- 动态测量 ----------------
    notes_lines: list[str] = []
    for note in notes:
        # 每行最多 30 个全角字符
        notes_lines.append(note[:60])
    top_items = stats.get("top_items", [])[:3]
    top_text = "、".join(f"{k} ×{v}" for k, v in top_items) if top_items else "暂无复购数据"

    header_h = 250
    axis_block_h = 46 + 4 * 58 + 20            # 标题 + 四轴行
    ing_block_h = 46 + len(ing) * 40 + 20      # 标题 + 成分行
    stats_h = 96
    notes_block_h = 40 + len(notes_lines) * 26 + 16
    tip_h = 78
    footer_h = 46

    y = 30
    parts: list[str] = []

    # ---------------- 画布与纸面 ----------------
    total_h = y + header_h + 26 + axis_block_h + 22 + ing_block_h + 22 + stats_h + 20 + notes_block_h + 22 + tip_h + 20 + footer_h
    parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {total_h}" width="{width}" height="{total_h}">')
    parts.append(f'<rect width="{width}" height="{total_h}" fill="{PAPER}"/>')
    # 顶部品牌条
    parts.append(f'<rect width="{width}" height="10" fill="{RED}"/>')
    parts.append(f'<rect y="10" width="{width}" height="5" fill="{YELLOW}"/>')

    # ---------------- 头部 ----------------
    cy = y + 56
    parts.append(_t(width / 2, cy, 30, INK, "麦门人格鉴定所", "middle", "800", 8))
    parts.append(_t(width / 2, cy + 30, 13, GREY, "MCDONALD'S MBTI LAB · 基于真实订单数据的赛博人格分析", "middle", "400", 2))

    # 人格代号（黄色底红字，徽章式）
    badge_w = 46 + len(code) * 52
    bx = (width - badge_w) / 2
    by = cy + 62
    parts.append(f'<rect x="{bx}" y="{by}" width="{badge_w}" height="104" rx="14" fill="{RED}"/>')
    parts.append(f'<rect x="{bx + 5}" y="{by + 5}" width="{badge_w - 10}" height="94" rx="10" fill="none" stroke="{YELLOW}" stroke-width="2"/>')
    for i, ch in enumerate(code):
        parts.append(_t(width / 2 - (len(code) - 1) * 26 + i * 52, by + 72, 60, "#FFFFFF", ch, "middle", "800"))

    ny = by + 104 + 36
    parts.append(_t(width / 2, ny, 24, DARK_RED, f"{persona['name']} · {persona['confidence']}", "middle", "700"))
    parts.append(_t(width / 2, ny + 26, 14, GREY, persona["tagline"], "middle", "400"))

    y = ny + 26 + 24

    # ---------------- 四轴天平 ----------------
    parts.append(f'<rect x="40" y="{y}" width="{width - 80}" height="{axis_block_h}" rx="10" fill="{CREAM}" stroke="#E8DCC0" stroke-width="1"/>')
    parts.append(_t(60, y + 30, 15, INK, "⚖️ 四轴天平", "start", "700"))
    ay = y + 58
    for axis in ("EI", "SN", "TF", "JP"):
        label, pole_a, pole_b, color_a, color_b = AXIS_META[axis]
        score = scores[axis]
        # 每个轴的「高分极」：得分 > 50 时该极占比 = score%
        high_pole = {"EI": "E", "SN": "N", "TF": "F", "JP": "J"}[axis]
        left_letter, right_letter = pole_a, pole_b
        if left_letter == high_pole:
            left_ratio, right_ratio = score / 100, 1 - score / 100
        else:
            left_ratio, right_ratio = 1 - score / 100, score / 100
        dominant = left_letter if left_ratio >= right_ratio else right_letter
        # 轴标签
        parts.append(_t(60, ay + 16, 13, INK, label, "start", "700"))
        parts.append(_t(60, ay + 34, 11, GREY, f"{left_letter} · {right_letter}", "start"))
        # 天平条
        bar_x, bar_w = 190, 380
        parts.append(f'<rect x="{bar_x}" y="{ay + 4}" width="{bar_w}" height="22" rx="11" fill="#EFE6D0"/>')
        dom_ratio = left_ratio if dominant == left_letter else right_ratio
        fill_w = max(11, bar_w * dom_ratio)
        dom_color = color_a if dominant == left_letter else color_b
        parts.append(f'<rect x="{bar_x}" y="{ay + 4}" width="{fill_w}" height="22" rx="11" fill="{dom_color}"/>')
        # 字母标注
        la_color = color_a if left_letter == dominant else GREY
        rb_color = color_b if right_letter == dominant else GREY
        parts.append(_t(bar_x - 14, ay + 20, 13, la_color, left_letter, "end", "800" if left_letter == dominant else "400"))
        parts.append(_t(bar_x + bar_w + 14, ay + 20, 13, rb_color, right_letter, "start", "800" if right_letter == dominant else "400"))
        parts.append(_t(bar_x + bar_w + 52, ay + 20, 13, INK, f"{dominant} {int(round(dom_ratio * 100))}%", "start", "700"))
        ay += 58

    y += axis_block_h + 22

    # ---------------- 麦门成分 ----------------
    parts.append(f'<rect x="40" y="{y}" width="{width - 80}" height="{ing_block_h}" rx="10" fill="{CREAM}" stroke="#E8DCC0" stroke-width="1"/>')
    parts.append(_t(60, y + 30, 15, INK, "🧪 麦门成分", "start", "700"))
    iy = y + 56
    for name, value in ing.items():
        parts.append(_t(60, iy + 14, 13, INK, name, "start", "600"))
        bar_x, bar_w = 170, 400
        parts.append(f'<rect x="{bar_x}" y="{iy + 2}" width="{bar_w}" height="18" rx="9" fill="#EFE6D0"/>')
        parts.append(f'<rect x="{bar_x}" y="{iy + 2}" width="{bar_w * value / 100}" height="18" rx="9" fill="{YELLOW}"/>')
        parts.append(f'<rect x="{bar_x + bar_w * value / 100 - 2}" y="{iy + 2}" width="4" height="18" fill="{RED}"/>')
        parts.append(_t(bar_x + bar_w + 12, iy + 16, 13, DARK_RED, f"{value}%", "start", "700"))
        iy += 40

    y += ing_block_h + 22

    # ---------------- 真实数据统计 ----------------
    n = stats.get("order_count", 0)
    if n:
        cells = [
            ("鉴定样本", f"{n} 单"),
            ("累计消费", f"¥{stats['total_spend']}"),
            ("场均客单", f"¥{stats['avg_spend']}"),
            ("足迹门店", f"{stats['store_count']} 家"),
        ]
        cw = (width - 80) / 4
        parts.append(f'<rect x="40" y="{y}" width="{width - 80}" height="{stats_h}" rx="10" fill="{INK}"/>')
        for i, (k, v) in enumerate(cells):
            cx = 40 + cw * i + cw / 2
            parts.append(_t(cx, y + 40, 12, "#B9B2A4", k, "middle"))
            parts.append(_t(cx, y + 70, 22, YELLOW, v, "middle", "700"))
            if i:
                parts.append(f'<line x1="{40 + cw * i}" y1="{y + 22}" x2="{40 + cw * i}" y2="{y + 74}" stroke="#4A463C" stroke-width="1"/>')
        y += stats_h + 20

    # ---------------- 行为分析 ----------------
    parts.append(f'<rect x="40" y="{y}" width="{width - 80}" height="{notes_block_h}" rx="10" fill="{CREAM}" stroke="#E8DCC0" stroke-width="1"/>')
    parts.append(_t(60, y + 30, 15, INK, "🔍 行为分析（基于真实订单）", "start", "700"))
    ny2 = y + 58
    for line in notes_lines:
        parts.append(f'<circle cx="66" cy="{ny2 - 4}" r="3" fill="{RED}"/>')
        parts.append(_t(78, ny2, 13, "#4A4438", line, "start"))
        ny2 += 26
    y += notes_block_h + 22

    # ---------------- 相处指南 ----------------
    parts.append(f'<rect x="40" y="{y}" width="{width - 80}" height="{tip_h}" rx="10" fill="{RED}"/>')
    parts.append(f'<rect x="45" y="{y + 5}" width="{width - 90}" height="{tip_h - 10}" rx="8" fill="none" stroke="{YELLOW}" stroke-width="1.5"/>')
    parts.append(_t(60, y + 32, 15, YELLOW, "🤝 相处指南", "start", "700"))
    parts.append(_t(60, y + 58, 14, "#FFE9D6", persona["tip"], "start"))
    y += tip_h + 20

    # ---------------- 页脚 ----------------
    parts.append(_t(width / 2, y + 22, 12, GREY, "赛博玄学 · 数据来源：麦当劳 MCP · 仅供娱乐", "middle"))
    parts.append("</svg>")
    return "\n".join(parts)
