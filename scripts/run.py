#!/usr/bin/env python3
"""麦门人格鉴定所 · 命令行入口。

用法：
    python scripts/run.py --mock                      # 演示模式（内置模拟订单，无需 Token）
    python scripts/run.py                              # 正式模式，读取环境变量 MCD_MCP_TOKEN
    python scripts/run.py --token YOUR_TOKEN
    python scripts/run.py --mock --text                # 只输出纯文本鉴定报告

输出：
    output/persona.svg        人格鉴定卡（可直接分享）
    output/persona.json       结构化鉴定数据
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcd_client import McDClient, safe_call  # noqa: E402
from persona import build_persona, format_text  # noqa: E402
from render_card import build_svg  # noqa: E402

# 与 order-list 真实返回一致的 Markdown 样本（10 单，取自真实账户数据脱敏结构）
MOCK_ORDERS = """# API Response Information

Below is the response from an API call.

## Response Structure

> Content-Type: application/json

- **data**: No comments found. (Type: object)
  - **data.list**: 订单列表 (Type: array)
    - **data.list[].orderId**: 订单编码 (Type: string)
    - **data.list[].createTime**: 下单时间 (Type: string)
    - **data.list[].storeName**: 门店名称 (Type: string)
    - **data.list[].realTotalAmount**: 实付金额 (Type: string)
    - **data.list[].orderProductList**: 商品 (Type: array)

## Original Response

{"success":true,"code":200,"message":"请求成功","datetime":"2026-10-12 14:00:00","data":{"list":[
{"orderId":"1030555330000795083289542354","orderType":"1","createTime":"2026-09-18 21:46:47","beType":"1","storeCode":"3230214","storeName":"麦当劳沈阳元江街餐厅","orderStatus":"订单已完成","realTotalAmount":"38.5","orderProductList":[{"productCode":"9900015955","productName":"三文鱼双虾至尊月堡四件套","quantity":1,"comboItemList":[{"productCode":"521903","name":"三文鱼双虾至尊月堡","quantity":1},{"productCode":"521901","name":"月下相思扭扭薯","quantity":1},{"productCode":"1700","name":"麦辣鸡翅2块","quantity":1},{"productCode":"521904","name":"举杯邀月柚桂茶(冰)","quantity":1}]}]},
{"orderId":"1030555330000795083289542355","orderType":"1","createTime":"2026-09-18 21:34:38","beType":"1","storeCode":"3230214","storeName":"麦当劳沈阳元江街餐厅","orderStatus":"订单已完成","realTotalAmount":"29.8","orderProductList":[{"productCode":"9900015956","productName":"圆筒冰淇淋","quantity":1,"comboItemList":[]},{"productCode":"9900015957","productName":"大薯条","quantity":1,"comboItemList":[]},{"productCode":"9900015958","productName":"人气经典随心配","quantity":1,"comboItemList":[{"productCode":"521000","name":"麦香鱼","quantity":1},{"productCode":"521001","name":"可乐麦炫酷","quantity":1}]}]},
{"orderId":"1030555330000795083289542356","orderType":"1","createTime":"2026-09-07 21:17:10","beType":"1","storeCode":"3230215","storeName":"麦当劳沈阳西江街中海城锦","orderStatus":"订单已完成","realTotalAmount":"71.8","orderProductList":[{"productCode":"9900015959","productName":"下午茶搭子小食2+2","quantity":1,"comboItemList":[{"productCode":"1700","name":"麦辣鸡翅2块","quantity":1},{"productCode":"521902","name":"那么大鸡排（椒盐风味）","quantity":1},{"productCode":"521100","name":"中薯条","quantity":1}]},{"productCode":"9900015960","productName":"大堡口福五件套(麦金卡免配)","quantity":1,"comboItemList":[{"productCode":"521200","name":"新加坡蟹酱风味海鲜堡","quantity":1},{"productCode":"521201","name":"大薯条","quantity":1},{"productCode":"521202","name":"麦乐鸡5块","quantity":1},{"productCode":"521203","name":"菠萝派","quantity":1},{"productCode":"521204","name":"可口可乐大杯","quantity":1}]},{"productCode":"9900015961","productName":"麦辣鸡腿汉堡","quantity":1,"comboItemList":[]}]},
{"orderId":"1030555330000795083289542357","orderType":"1","createTime":"2026-08-24 15:01:53","beType":"1","storeCode":"3230214","storeName":"麦当劳沈阳元江街餐厅","orderStatus":"订单已完成","realTotalAmount":"46.4","orderProductList":[{"productCode":"9900015962","productName":"下午茶搭子小食2+2","quantity":1,"comboItemList":[{"productCode":"1700","name":"麦辣鸡翅2块","quantity":1},{"productCode":"521100","name":"中薯条","quantity":1}]},{"productCode":"9900015963","productName":"大堡口福五件套(新加坡蟹酱风味海鲜堡)(麦金卡免配)","quantity":1,"comboItemList":[{"productCode":"521200","name":"新加坡蟹酱风味海鲜堡","quantity":1},{"productCode":"521201","name":"大薯条","quantity":1},{"productCode":"521205","name":"马来咖喱风味薄皮肉骨鸡","quantity":1},{"productCode":"521203","name":"菠萝派","quantity":1},{"productCode":"521206","name":"美禄可可雪冰","quantity":1}]}]},
{"orderId":"1030555330000795083289542358","orderType":"1","createTime":"2026-08-13 13:55:56","beType":"1","storeCode":"3230216","storeName":"麦当劳沈阳沃尔玛餐厅","orderStatus":"订单已完成","realTotalAmount":"53.3","orderProductList":[{"productCode":"9900015964","productName":"蘸酱韩式甜辣酱鸡块","quantity":1,"comboItemList":[{"productCode":"521207","name":"韩式甜辣酱鸡块","quantity":1},{"productCode":"521208","name":"日式鲜磨山葵酱","quantity":1}]},{"productCode":"9900015965","productName":"人气超值四件套随心选","quantity":1,"comboItemList":[{"productCode":"521300","name":"板烧鸡腿堡","quantity":1},{"productCode":"521100","name":"中薯条","quantity":1},{"productCode":"521209","name":"麦辣大四角（山葵酱）","quantity":1},{"productCode":"521210","name":"可乐中杯","quantity":1}]},{"productCode":"9900015966","productName":"人气经典随心配","quantity":1,"comboItemList":[{"productCode":"521301","name":"麦香鸡","quantity":1},{"productCode":"521211","name":"怡泉+C麦炫酷","quantity":1}]}]},
{"orderId":"1030555330000795083289542359","orderType":"1","createTime":"2026-08-09 20:38:27","beType":"1","storeCode":"3230215","storeName":"麦当劳沈阳西江街中海城锦","orderStatus":"订单已完成","realTotalAmount":"6","orderProductList":[{"productCode":"9900015967","productName":"下午茶搭子小食2+2","quantity":1,"comboItemList":[{"productCode":"521100","name":"中薯条","quantity":1}]},{"productCode":"9900015968","productName":"【美汁源】“多汁柠柠”","quantity":1,"comboItemList":[]}]},
{"orderId":"1030555330000795083289542360","orderType":"1","createTime":"2026-08-07 10:52:49","beType":"1","storeCode":"3230215","storeName":"麦当劳沈阳西江街中海城锦","orderStatus":"订单已完成","realTotalAmount":"44.9","orderProductList":[{"productCode":"9900015969","productName":"下午茶搭子小食2+2","quantity":1,"comboItemList":[{"productCode":"521100","name":"中薯条","quantity":1}]},{"productCode":"9900015970","productName":"鱼牛汉堡随心选单人餐【升级小食送酱】","quantity":1,"comboItemList":[{"productCode":"521302","name":"不素之霸双层牛堡","quantity":1},{"productCode":"521209","name":"麦辣大四角（山葵酱）","quantity":1},{"productCode":"521201","name":"大薯条","quantity":1},{"productCode":"521211","name":"【美汁源】“多汁柠柠”","quantity":1}]}]},
{"orderId":"1030555330000795083289542361","orderType":"1","createTime":"2026-08-05 11:26:15","beType":"1","storeCode":"3230215","storeName":"麦当劳沈阳西江街中海城锦","orderStatus":"订单已完成","realTotalAmount":"63.9","orderProductList":[{"productCode":"9900015971","productName":"下午茶搭子小食2+2","quantity":1,"comboItemList":[{"productCode":"521100","name":"中薯条","quantity":1}]},{"productCode":"9900015972","productName":"鱼牛汉堡随心选单人餐【升级小食送酱】","quantity":1,"comboItemList":[{"productCode":"521303","name":"培根蔬萃双层牛堡","quantity":1},{"productCode":"521209","name":"麦辣大四角（山葵酱）","quantity":1},{"productCode":"521201","name":"大薯条","quantity":1},{"productCode":"521211","name":"【美汁源】“多汁柠柠”","quantity":1}]}]},
{"orderId":"1030555330000795083289542362","orderType":"1","createTime":"2026-08-03 20:31:53","beType":"1","storeCode":"3230215","storeName":"麦当劳沈阳西江街中海城锦","orderStatus":"订单已完成","realTotalAmount":"41.4","orderProductList":[{"productCode":"9900015973","productName":"下午茶搭子小食2+2","quantity":1,"comboItemList":[{"productCode":"521100","name":"中薯条","quantity":1}]},{"productCode":"9900015974","productName":"美芝芝拉丝鸡肉堡单人餐【升级小食送酱】","quantity":1,"comboItemList":[{"productCode":"521304","name":"美芝芝拉丝鸡肉堡","quantity":1},{"productCode":"521212","name":"麦辣大四角（牧场酱）","quantity":1},{"productCode":"521213","name":"柠檬脆脆麦旋风","quantity":1},{"productCode":"521214","name":"可口可乐中杯","quantity":1}]}]},
{"orderId":"1030555330000795083289542363","orderType":"1","createTime":"2026-08-01 10:36:54","beType":"1","storeCode":"3230215","storeName":"麦当劳沈阳西江街中海城锦","orderStatus":"订单已完成","realTotalAmount":"6","orderProductList":[{"productCode":"9900015975","productName":"下午茶搭子小食2+2","quantity":1,"comboItemList":[{"productCode":"521215","name":"那么大鸡排（椒盐风味）","quantity":1},{"productCode":"521100","name":"中薯条","quantity":1}]}]}
]}}
"""

MOCK_COUPONS = """# 您的优惠券列表

共 11 张可用优惠券 | 第 1/1 页 | 每页 200 条

## 中薯条买一送一
- **优惠**: ¥13.5 (用券价格)
- **有效期**: 2026-10-12 10:30-2026-10-16 23:59 周一、二、三、四、五 10:30-23:59
- **标签**: 到店专用、外送专用

## 麦辣鸡腿堡套餐兑换券
- **优惠**: 免费兑换
- **有效期**: 2026-10-13 23:59
- **标签**: 到店专用
"""


def gather(client: McDClient) -> dict:
    """按顺序调取人格鉴定所需的 MCP 数据，单个工具失败不影响整体。"""
    plan = [
        ("order-list", {}),
        ("query-my-coupons", {}),
        ("query-my-account", {}),
        ("list-nutrition-foods", {}),
    ]
    data, errors = {}, {}
    for name, args in plan:
        result, err = safe_call(client, name, args)
        data[name] = result
        if err:
            errors[name] = err
    return {"data": data, "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser(description="麦门人格鉴定所")
    parser.add_argument("--token", default=os.environ.get("MCD_MCP_TOKEN"), help="麦当劳 MCP Token（也可用环境变量 MCD_MCP_TOKEN）")
    parser.add_argument("--out", default="output", help="输出目录")
    parser.add_argument("--mock", action="store_true", help="使用内置模拟订单，无需 Token")
    parser.add_argument("--text", action="store_true", help="只输出纯文本鉴定报告")
    args = parser.parse_args()

    if args.mock:
        raw = {"order-list": MOCK_ORDERS, "query-my-coupons": MOCK_COUPONS}
        errors = {}
    else:
        if not args.token:
            print("❌ 未提供 MCP Token。请：")
            print("   1. 前往 https://open.mcd.cn/mcp 用手机号登录并申请 Token")
            print("   2. 设置环境变量 MCD_MCP_TOKEN 或使用 --token 参数")
            print("   （或先用 --mock 体验演示模式）")
            return 1
        client = McDClient(args.token)
        try:
            client.initialize()
        except Exception as exc:  # noqa: BLE001
            print(f"❌ MCP 连接失败：{exc}")
            return 1
        gathered = gather(client)
        raw, errors = gathered["data"], gathered["errors"]
        if errors:
            for name, err in errors.items():
                print(f"⚠️ {name} 调用失败：{err}")

    persona = build_persona(
        orders_raw=raw.get("order-list"),
        coupons_raw=raw.get("query-my-coupons"),
        account_raw=raw.get("query-my-account"),
        foods_raw=raw.get("list-nutrition-foods"),
    )

    print(format_text(persona))

    if args.text:
        return 0

    os.makedirs(args.out, exist_ok=True)
    svg_path = os.path.join(args.out, "persona.svg")
    json_path = os.path.join(args.out, "persona.json")
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(build_svg(persona))
    import json
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(persona, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n🧬 人格鉴定卡：{svg_path}")
    print(f"📦 结构化数据：{json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
