"""麦门人格鉴定所 · MBTI 分析引擎。

输入：麦当劳 MCP 真实数据（点餐订单 / 我的券 / 积分账户 / 餐品营养表）
输出：麦门 MBTI 人格鉴定（四轴评分 + 16 型人格 + 麦门成分 + 行为分析）

四轴设计（全部可从真实订单数据计算）：
- E / I  社交能量轴：大份量多件套 vs 一人食小份
- S / N  点单风格轴：经典长青款 vs 新品限定猎奇
- T / F  消费决策轴：精算凑单 vs 氛围豪掷
- J / P  时间节律轴：固定时段规律干饭 vs 随机浪人深夜档

设计原则：
- 所有评分只使用真实数据，不编造；
- 数据不足（< 3 单）时降级为「尝鲜体验版」，明确告知样本量；
- 同日多次鉴定结果一致（纯数据驱动，无随机漂移）。
"""

from __future__ import annotations

import datetime as dt
import json
import re
from typing import Any

# --------------------------------------------------------------------------- #
# 词表
# --------------------------------------------------------------------------- #

# 经典长青款（上市多年、菜单常驻）——不在表内的视为尝鲜向
CLASSIC_PRODUCTS = {
    "麦辣鸡腿堡", "麦辣鸡腿汉堡", "板烧鸡腿堡", "板烧鸡腿汉堡", "巨无霸",
    "麦香鱼", "麦香鸡", "麦乐鸡", "双层吉士堡", "吉士堡", "安格斯厚牛堡",
    "薯条", "大薯条", "中薯条", "小薯条", "可乐", "可口可乐", "零度可乐",
    "菠萝派", "香芋派", "苹果派", "薯饼", "麦满分", "猪柳蛋堡", "猪柳麦满分",
    "烟肉蛋麦满分", "玉米杯", "鲜煮咖啡", "冰美式", "美式咖啡", "拿铁",
    "草莓新地", "巧克力新地", "麦旋风", "圆筒冰淇淋", "甜筒", "麦辣鸡翅",
    "那么大鸡排", " share桶", "分享桶", "麦香鱼堡",
}

# 辣味关键词（嗜辣度）
SPICY_KEYWORDS = ["麦辣", "辣酱", "椒盐", "山葵", "芥末", "辣味", "麻辣", "辣椒"]

# 新品/限定信号词（猎奇度加成）
NOVELTY_KEYWORDS = [
    "限定", "联名", "季节", "上新", "新品", "月", "蟹酱", "韩式", "拉丝",
    "蔬萃", "山葵", "肉骨", "双虾", "三文鱼", "柚桂", "多汁柠柠", "扭扭薯",
    "马来", "新加坡", "美芝芝", "脆脆", "麦炫酷", "雪冰",
]

# 大份量/分享型套餐关键词（社交能量 E 向）
BIG_COMBO_KEYWORDS = ["四件套", "五件套", "六件套", "分享桶", "小食2+2", "2+2", "家庭", "双人"]

# 一人食关键词（社交能量 I 向）
SOLO_KEYWORDS = ["单人餐", "随心配", "单人", "一份", "小食拼"]

# 深夜档（21 点及以后）
LATE_NIGHT_HOUR = 21

# --------------------------------------------------------------------------- #
# 16 型人格
# --------------------------------------------------------------------------- #
TYPES: dict[str, dict[str, str]] = {
    "ISTJ": {
        "name": "麦门会计师",
        "tagline": "固定窗口，固定餐品，固定人生",
        "desc": "你的点单记录像一本台账：经典款、老门店、固定时段，分文不乱。你不是不爱新品，只是旧爱从未辜负。",
        "portrait": "经典老三样 + 老位置 + 准点出现，消费曲线平直得像期望值。",
        "tip": "和 TA 拼单直接报餐品名，别问「想吃什么」，问就是老三样。",
    },
    "ISFJ": {
        "name": "麦门守夜人",
        "tagline": "默默领券的人，温柔得让人心疼",
        "desc": "你总在别人下班后才出现在取餐柜前，不争不抢，券却一个没落。你的麦门哲学是：不声张，但照顾好自己的胃。",
        "portrait": "夜间档常客，领券数量远超点单数量，经典款为主。",
        "tip": "TA 的券比你多，拼单时让 TA 出手，你负责夸。",
    },
    "ESTJ": {
        "name": "麦门纪律委员",
        "tagline": "干饭也要讲流程和性价比",
        "desc": "你把一顿麦当劳吃成了项目管理：什么时段、哪家店、用哪张券、凑哪个满减，全部有理有据。经典款是你的基本盘。",
        "portrait": "规律时段 + 经典款 + 客单价稳定，偶尔带队拼单。",
        "tip": "别跟 TA 争论怎么点最划算，TA 有台账。",
    },
    "ESFJ": {
        "name": "麦门群主",
        "tagline": "拼单群群主，喂饱全办公室",
        "desc": "你的订单永远不止一份：大堡口福五件套、小食 2+2，顺手还能帮三个同事带。麦当劳的分享属性被你拉满。",
        "portrait": "大份量多件套高频，客单价高，门店固定，人缘极好。",
        "tip": "抱住这个大腿，TA 拼单时你只负责说「我要麦辣鸡腿堡」。",
    },
    "ISTP": {
        "name": "麦门匠人",
        "tagline": "单品大师，酱料科学家",
        "desc": "你不追求花哨，追求精准：哪款汉堡配哪款酱、薯条几分几秒口感最好，你心里有数。订单不多，但每一单都是作品。",
        "portrait": "订单数少而精，小食/酱料/单品重复出现，经典与猎奇混合。",
        "tip": "TA 推荐酱料组合时，闭嘴接受就行。",
    },
    "ISFP": {
        "name": "麦门艺术家",
        "tagline": "派品收藏家，新地鉴赏员",
        "desc": "你对麦当劳的爱是细腻的：新地要草莓的，派要菠萝的，麦旋风要限定口味。不求吃饱，追求那一刻的甜。",
        "portrait": "甜品/派/新地占比高，客单价偏低，节奏随性。",
        "tip": "送 TA 一个新地，比说十句话都管用。",
    },
    "ESTP": {
        "name": "麦门突击手",
        "tagline": "想吃就点，辣度拉满",
        "desc": "你的麦门字典里没有「等等再说」：看到新品上架当天就冲，麦辣鸡翅一次两块。行动力全部门店第一。",
        "portrait": "猎奇度高 + 嗜辣度高 + 下单决策快，深夜档常见。",
        "tip": "跟 TA 出门吃饭永远不用做攻略。",
    },
    "ESFP": {
        "name": "麦门氛围组",
        "tagline": "快乐水传递者，聚餐发动机",
        "desc": "你点的不是麦当劳，是热闹：小食拼盘摆一桌，可乐必须大杯。有你在的拼单群，永远不缺表情包。",
        "portrait": "大份量 + 高社交 + 时段随缘，客单价中高。",
        "tip": "氛围担当，拼单时负责把「吃什么」聊成「都点都点」。",
    },
    "INFJ": {
        "name": "麦门先知",
        "tagline": "深夜下单的人，心里都有一片海",
        "desc": "你在 21 点后出现的次数比太阳还准。别人是饿了，你是需要一个出口。麦辣鸡腿堡的温度，刚好接住你的情绪。",
        "portrait": "深夜档高频，经典款为主，独食为主，消费理性。",
        "tip": "TA 深夜下单时别劝「少吃点」，陪 TA 吃。",
    },
    "INFP": {
        "name": "麦门诗人",
        "tagline": "一根薯条，一首诗",
        "desc": "你对麦当劳有自己的一套美学：扭扭薯要扭得均匀，新地要挖得整齐。订单里藏着你的情绪周期，甜食是你的暗号。",
        "portrait": "甜品/小食偏好，深夜或下午茶出没，客单价低但频次稳。",
        "tip": "和 TA 分享一根薯条，就是交情。",
    },
    "INTJ": {
        "name": "麦门军师",
        "tagline": "薅羊毛界的战略家",
        "desc": "别人薅羊毛靠运气，你靠推演：券怎么叠、积分何时用、哪个渠道便宜三块五，全部在射程之内。新品你也试，但必须在期望值为正时。",
        "portrait": "精算度极高 + 经典款基本盘 + 客单价被精准控制在甜蜜点。",
        "tip": "TA 说「这单等我算算」的时候，真的在算。",
    },
    "INTP": {
        "name": "麦门研究员",
        "tagline": "成分表阅读爱好者",
        "desc": "你点单前真的会看营养表：蛋白质多少克、钠是不是超了、这款新品的碳水结构如何。麦当劳对你既是食堂也是实验室。",
        "portrait": "猎奇与经典混合，理性消费，对营养数据敏感。",
        "tip": "别问 TA「好吃吗」，问「营养结构如何」。",
    },
    "ENFJ": {
        "name": "麦门暖心人",
        "tagline": "投喂型人格，拼单永动机",
        "desc": "你记得每个同事爱吃什么，取餐时永远多拿一袋薯条。麦当劳的社交属性被你开发到了极致。",
        "portrait": "多件套高频 + 时段规律 + 经典与猎奇兼有。",
        "tip": "TA 记得你的口味，你也最好记得 TA 的。",
    },
    "ENFP": {
        "name": "麦门竞选者",
        "tagline": "限定款雷达，快乐传播者",
        "desc": "麦当劳每次上新，你的雷达比官方公众号还灵。月堡、联名帽、限定酱，你全都要第一时间尝鲜，然后安利全世界。",
        "portrait": "新品率极高，时段分散，客单价随心情波动。",
        "tip": "关注 TA 的朋友圈，等于关注麦当劳新品日历。",
    },
    "ENTJ": {
        "name": "麦门指挥官",
        "tagline": "早餐战略，晚餐决胜",
        "desc": "你把麦当劳吃成了日程表：早餐吃什么补充蛋白质、加班夜点什么续命，全部服务于你的人生 KPI。点单即决策，从不含糊。",
        "portrait": "规律时段 + 高客单 + 大份量，效率至上。",
        "tip": "TA 的日程表里，「吃饭」也是带 OKR 的。",
    },
    "ENTP": {
        "name": "麦门发明家",
        "tagline": "蘸酱混搭第一人",
        "desc": "你的订单从不标准：甜辣酱配麦乐鸡、山葵酱配大鸡排，万物皆可混搭。麦当劳的菜单对你来说只是原材料。",
        "portrait": "猎奇度极高 + 小食/酱料重复出现 + 消费随创意波动。",
        "tip": "TA 递过来的「黑暗料理」，尝尝，可能真香。",
    },
}

# 四轴说明（用于卡片展示）
AXIS_LABELS = {
    "EI": ("社交能量", "E·麦门社交官", "I·孤独美食家"),
    "SN": ("点单风格", "S·经典守卫者", "N·猎奇尝鲜家"),
    "TF": ("消费决策", "T·精算指挥官", "F·氛围鉴赏家"),
    "JP": ("时间节律", "J·规律干饭人", "P·随机浪人"),
}


# --------------------------------------------------------------------------- #
# 数据解析（MCP 返回 Markdown + Original Response JSON）
# --------------------------------------------------------------------------- #
def _extract_text(raw: Any) -> str:
    if raw is None:
        return ""
    if isinstance(raw, str):
        return raw
    if isinstance(raw, dict):
        if isinstance(raw.get("_raw"), str):
            return raw["_raw"]
        content = raw.get("content")
        if isinstance(content, list):
            texts = [c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text"]
            if texts:
                return "\n".join(texts)
        for key in ("text", "markdown"):
            if isinstance(raw.get(key), str):
                return raw[key]
        return ""
    return str(raw)


def _extract_original_json(raw: Any) -> dict | None:
    text = _extract_text(raw)
    m = re.search(r"##\s*Original Response\s*\n+(\{.*)", text, re.S)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except ValueError:
            return None
    stripped = text.strip()
    if stripped.startswith("{"):
        try:
            return json.loads(stripped)
        except ValueError:
            return None
    return None


def parse_orders(raw: Any) -> list[dict]:
    """从 order-list 中提取订单列表（含商品明细）。"""
    j = _extract_original_json(raw)
    data = (j or {}).get("data")
    if not isinstance(data, dict):
        return []
    orders = []
    for o in data.get("list", []):
        if not isinstance(o, dict):
            continue
        items = []
        for p in o.get("orderProductList", []):
            if not isinstance(p, dict):
                continue
            name = p.get("productName", "")
            if not name:
                continue
            subs = [c.get("name", "") for c in p.get("comboItemList", []) if isinstance(c, dict) and c.get("name")]
            items.append({
                "name": name,
                "qty": int(p.get("quantity", 1) or 1),
                "subs": subs,
            })
        orders.append({
            "time": o.get("createTime", ""),
            "amount": _to_float(o.get("realTotalAmount")) or 0.0,
            "store": o.get("storeName", ""),
            "status": o.get("orderStatus", ""),
            "items": items,
        })
    return orders


def _to_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        m = re.search(r"-?\d+(?:\.\d+)?", value.replace(",", ""))
        if m:
            return float(m.group())
    return None


def parse_coupon_count(raw: Any) -> int:
    """从 query-my-coupons 的 Markdown 中统计「我的券」数量（## 券名 小节数）。"""
    text = _extract_text(raw)
    if not text:
        return 0
    m = re.search(r"共\s*(\d+)\s*张", text)
    if m:
        return int(m.group(1))
    count = 0
    for block in re.split(r"^##\s+", text, flags=re.M)[1:]:
        name = block.split("\n", 1)[0].strip()
        if name and name not in ("Original Response", "Response Structure"):
            count += 1
    return count


def parse_food_names(raw: Any) -> list[str]:
    """从 list-nutrition-foods 中提取餐品名（CSV 文本）。"""
    j = _extract_original_json(raw)
    data = (j or {}).get("data")
    names = []
    if isinstance(data, str):
        for line in data.split("\n"):
            line = line.strip()
            if not line or line.startswith("{") or line.startswith("["):
                continue
            first = line.split(",")[0].strip()
            if first:
                names.append(first)
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and item.get("productName"):
                names.append(str(item["productName"]))
    return names


# --------------------------------------------------------------------------- #
# 特征聚合
# --------------------------------------------------------------------------- #
def _is_classic(name: str) -> bool:
    n = name.replace(" ", "")
    return any(c.replace(" ", "") in n or n in c.replace(" ", "") for c in CLASSIC_PRODUCTS)


def _has_any(name: str, keywords: list[str]) -> bool:
    return any(k in name for k in keywords)


def aggregate(orders: list[dict], coupon_count: int = 0) -> dict:
    """把订单列表聚合成人格评分所需的全部特征。"""
    if not orders:
        return {"order_count": 0}

    item_counter: dict[str, int] = {}
    total_items = 0
    classic_hits = 0
    novel_hits = 0
    spicy_hits = 0
    big_combo_orders = 0
    solo_orders = 0
    late_night = 0
    hours: list[int] = []
    amounts: list[float] = []
    stores: set[str] = set()

    for o in orders:
        amounts.append(o["amount"])
        stores.add(o["store"])
        hour = None
        m = re.search(r"(\d{1,2}):\d{2}", o["time"])
        if m:
            hour = int(m.group(1))
            hours.append(hour)
            if hour >= LATE_NIGHT_HOUR:
                late_night += 1
        order_text = " ".join(i["name"] for i in o["items"])
        for i in o["items"]:
            for sub in i["subs"]:
                item_counter[sub] = item_counter.get(sub, 0) + i["qty"]
            item_counter[i["name"]] = item_counter.get(i["name"], 0) + i["qty"]
            total_items += i["qty"]
            if _is_classic(i["name"]):
                classic_hits += 1
            for sub in i["subs"]:
                if _is_classic(sub):
                    classic_hits += 1
            if _has_any(i["name"], NOVELTY_KEYWORDS) or any(_has_any(s, NOVELTY_KEYWORDS) for s in i["subs"]):
                novel_hits += 1
            if _has_any(i["name"], SPICY_KEYWORDS) or any(_has_any(s, SPICY_KEYWORDS) for s in i["subs"]):
                spicy_hits += 1
        if _has_any(order_text, BIG_COMBO_KEYWORDS):
            big_combo_orders += 1
        if _has_any(order_text, SOLO_KEYWORDS):
            solo_orders += 1

    n = len(orders)
    classic_ratio = classic_hits / total_items if total_items else 0
    novel_ratio = novel_hits / total_items if total_items else 0
    spicy_ratio = spicy_hits / total_items if total_items else 0
    cheap_ratio = sum(1 for a in amounts if a < 30) / n
    rich_ratio = sum(1 for a in amounts if a >= 50) / n
    avg_items = total_items / n
    time_buckets = len({h // 4 for h in hours}) if hours else 0  # 0-5/6-9/10-13/14-17/18-20/21-23

    return {
        "order_count": n,
        "total_spend": round(sum(amounts), 1),
        "avg_spend": round(sum(amounts) / n, 1),
        "max_spend": round(max(amounts), 1),
        "min_spend": round(min(amounts), 1),
        "store_count": len(stores),
        "stores": sorted(stores),
        "avg_items": round(avg_items, 2),
        "classic_ratio": round(classic_ratio, 3),
        "novel_ratio": round(novel_ratio, 3),
        "spicy_ratio": round(spicy_ratio, 3),
        "big_combo_ratio": round(big_combo_orders / n, 3),
        "solo_ratio": round(solo_orders / n, 3),
        "late_night_ratio": round(late_night / n, 3),
        "time_buckets": time_buckets,
        "cheap_ratio": round(cheap_ratio, 3),
        "rich_ratio": round(rich_ratio, 3),
        "coupon_count": coupon_count,
        "top_items": sorted(item_counter.items(), key=lambda kv: kv[1], reverse=True)[:5],
    }


# --------------------------------------------------------------------------- #
# 四轴评分（0-100，>50 取第二个字母）
# --------------------------------------------------------------------------- #
def score_axes(f: dict) -> dict[str, int]:
    """根据聚合特征计算四轴得分。

    得分范围 5-95，各轴多数方字母对应的得分 > 50：
    EI > 50 → E（社交向）；SN > 50 → N（猎奇向）；
    TF <= 50 → T（精算向）；JP > 50 → J（规律向）。
    """
    if f.get("order_count", 0) < 3:
        return {"EI": 50, "SN": 50, "TF": 50, "JP": 50}

    # E/I：大套餐 + 商品数 → E；一人食 → I
    ei = 50 + (f["big_combo_ratio"] - f["solo_ratio"]) * 40 + (f["avg_items"] - 2.5) * 6
    ei = _clip(ei)

    # S/N：猎奇率直接映射（猎奇率 0.4 → 50；>0.6 偏 N）
    sn = 20 + f["novel_ratio"] * 100 + (1 - f["classic_ratio"]) * 15
    sn = _clip(sn)

    # T/F：低客单占比 + 领券数 → T；高客单 → F
    tf = 50 - f["cheap_ratio"] * 35 + f["rich_ratio"] * 25 - min(f["coupon_count"], 12) * 2.2
    tf = _clip(tf)

    # J/P：时段集中 → J；时段分散 + 深夜 → P
    jp = 50 + (3 - min(f["time_buckets"], 4)) * 8 - f["late_night_ratio"] * 40
    jp = _clip(jp)

    return {"EI": ei, "SN": sn, "TF": tf, "JP": jp}


def _letters(scores: dict[str, int]) -> dict[str, str]:
    """轴分 → 字母。多数方得分 > 50（TF 轴为 <= 50 取 T）。"""
    return {
        "EI": "E" if scores["EI"] > 50 else "I",
        "SN": "N" if scores["SN"] > 50 else "S",
        "TF": "T" if scores["TF"] <= 50 else "F",
        "JP": "J" if scores["JP"] > 50 else "P",
    }


def axis_display(axis: str, score: int) -> tuple[str, int]:
    """轴分 → (多数方字母, 多数方百分比)。"""
    letter = "E" if axis == "EI" else "N" if axis == "SN" else "F" if axis == "TF" else "J"
    if score > 50:
        return letter, score
    opposite = {"E": "I", "N": "S", "F": "T", "J": "P"}[letter]
    return opposite, 100 - score


def _clip(v: float) -> int:
    return max(5, min(95, int(round(v))))


# --------------------------------------------------------------------------- #
# 麦门成分（卡片条形图）
# --------------------------------------------------------------------------- #
def ingredients(f: dict) -> dict[str, int]:
    if f.get("order_count", 0) < 3:
        return {"猎奇度": 50, "嗜辣度": 50, "夜猫度": 50, "精算度": 50, "分享度": 50}
    return {
        "猎奇度": _clip(f["novel_ratio"] * 160),
        "嗜辣度": _clip(f["spicy_ratio"] * 200),
        "夜猫度": _clip(f["late_night_ratio"] * 160),
        "精算度": _clip(f["cheap_ratio"] * 110 + min(f["coupon_count"], 10) * 4),
        "分享度": _clip(f["big_combo_ratio"] * 130 + f["avg_items"] * 8),
    }


# --------------------------------------------------------------------------- #
# 人格鉴定
# --------------------------------------------------------------------------- #
def build_persona(
    orders_raw: Any = None,
    coupons_raw: Any = None,
    account_raw: Any = None,
    foods_raw: Any = None,
) -> dict:
    orders = parse_orders(orders_raw)
    coupon_count = parse_coupon_count(coupons_raw)
    foods = parse_food_names(foods_raw)

    f = aggregate(orders, coupon_count)
    axes_scores = score_axes(f)
    letters = _letters(axes_scores)
    code = "".join(letters[k] for k in ("EI", "SN", "TF", "JP"))
    profile = TYPES[code]

    # 数据充足度
    n = f.get("order_count", 0)
    confidence = "完整版" if n >= 8 else ("标准版" if n >= 3 else "尝鲜体验版")

    # 行为分析（真实数据驱动的结论文案）
    notes = _behavior_notes(f, letters)

    return {
        "code": code,
        "name": profile["name"],
        "tagline": profile["tagline"],
        "desc": profile["desc"],
        "portrait": profile["portrait"],
        "tip": profile["tip"],
        "letters": letters,
        "axis_scores": axes_scores,
        "confidence": confidence,
        "stats": f,
        "ingredients": ingredients(f),
        "notes": notes,
        "menu_size": len(foods),
        "data_sources": {
            "order-list": bool(orders),
            "query-my-coupons": coupon_count > 0,
            "query-my-account": account_raw is not None,
            "list-nutrition-foods": bool(foods),
        },
    }


def _behavior_notes(f: dict, letters: dict[str, str]) -> list[str]:
    """基于真实统计生成 3-5 条行为分析结论。"""
    notes: list[str] = []
    n = f.get("order_count", 0)
    if n < 3:
        return [f"当前仅获取到 {n} 个订单，样本不足以下定论——先去麦麦点几单，再来鉴定。"]
    notes.append(f"近 {n} 单累计消费 ¥{f['total_spend']}，场均 ¥{f['avg_spend']}，最贵一单 ¥{f['max_spend']}")
    if f["novel_ratio"] >= 0.5:
        notes.append(f"新品/限定命中率 {f['novel_ratio'] * 100:.0f}%，麦当劳上新你比官方积极")
    elif f["classic_ratio"] >= 0.6:
        notes.append(f"经典款占比 {f['classic_ratio'] * 100:.0f}%，老三样才是你的白月光")
    if f["spicy_ratio"] >= 0.3:
        notes.append(f"带辣订单占 {f['spicy_ratio'] * 100:.0f}%，无辣不欢实锤")
    if f["late_night_ratio"] >= 0.4:
        notes.append(f"21 点后订单占 {f['late_night_ratio'] * 100:.0f}%，深夜档固定玩家")
    if f["store_count"] >= 3:
        notes.append(f"足迹遍布 {f['store_count']} 家门店，麦门游牧民")
    elif f["store_count"] == 1:
        notes.append(f"只认准 {f['stores'][0][:14]}，恋旧型选手")
    if f["coupon_count"] >= 5:
        notes.append(f"手里躺着 {f['coupon_count']} 张券，领券达人")
    if f["top_items"]:
        top = "、".join(f"{k} ×{v}" for k, v in f["top_items"][:3])
        notes.append(f"复购之王：{top}")
    return notes[:6]


def format_text(persona: dict) -> str:
    """纯文本版鉴定报告（CLI / 无渲染环境兜底）。"""
    s = persona["stats"]
    lines = [
        f"🧬 麦门 MBTI 鉴定结果：{persona['code']} · {persona['name']}（{persona['confidence']}）",
        f"💬 {persona['tagline']}",
        f"📊 四轴：" + " · ".join(
            f"{AXIS_LABELS[k][0]} {axis_display(k, persona['axis_scores'][k])[0]} {axis_display(k, persona['axis_scores'][k])[1]}%"
            for k in ("EI", "SN", "TF", "JP")
        ),
        "",
        f"📖 {persona['desc']}",
        f"🍔 点单画像：{persona['portrait']}",
        "",
        "🔍 行为分析：",
    ]
    lines += [f"  · {note}" for note in persona["notes"]]
    if persona["ingredients"]:
        lines.append("")
        lines.append("🧪 麦门成分：" + " · ".join(f"{k} {v}%" for k, v in persona["ingredients"].items()))
    lines += ["", f"🤝 相处指南：{persona['tip']}",
              "—— 赛博玄学，数据来源：麦当劳 MCP，仅供娱乐 ——"]
    return "\n".join(lines)
