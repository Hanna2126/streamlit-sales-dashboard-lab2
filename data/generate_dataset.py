# -*- coding: utf-8 -*-
"""生成模拟电商订单数据（含脏数据），供数据看板实验使用。

业务场景：云栖优选自营电商 2026-01-01 ~ 2026-09-30 的订单明细。
产出：data/raw_orders.csv（含空值、负数、重复、异常值等脏数据）。
"""
from __future__ import annotations

import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

CATEGORIES = {
    "数码配件": (59.0, 899.0),
    "家居日用": (39.0, 399.0),
    "美妆个护": (49.0, 459.0),
    "运动户外": (89.0, 799.0),
    "食品生鲜": (19.0, 199.0),
    "图书文创": (29.0, 129.0),
}
CATEGORY_WEIGHTS = [0.24, 0.2, 0.19, 0.13, 0.14, 0.1]

CHANNELS = ["自营商城", "小程序", "直播间", "第三方平台"]
CHANNEL_WEIGHTS = [0.36, 0.28, 0.21, 0.15]

REGIONS = ["华东", "华南", "华北", "西南", "华中", "东北", "西北"]
REGION_WEIGHTS = [0.28, 0.22, 0.18, 0.13, 0.1, 0.05, 0.04]

MEMBER_LEVELS = ["普通会员", "银卡会员", "金卡会员", "钻石会员"]
MEMBER_WEIGHTS = [0.52, 0.26, 0.16, 0.06]

# 大促与季节性因子：开学季、618、暑期
PROMO_DAYS = {
    date(2026, 3, 1): (date(2026, 3, 8), 1.25),
    date(2026, 6, 15): (date(2026, 6, 20), 1.65),
    date(2026, 9, 1): (date(2026, 9, 10), 1.35),
}


def _promo_factor(d: date) -> float:
    for start, (end, factor) in PROMO_DAYS.items():
        if start <= d <= end:
            return factor
    return 1.0


def _daily_orders(d: date) -> int:
    """日订单量：基础量 + 周末效应 + 月度增长 + 大促因子 + 随机波动。"""
    base = 8 + (d.month - 1) * 1.2
    weekend = 1.15 if d.weekday() >= 5 else 1.0
    noise = random.uniform(0.85, 1.15)
    return max(3, int(round(base * weekend * _promo_factor(d) * noise)))


def _make_order(order_id: int, d: date) -> dict:
    category = random.choices(list(CATEGORIES), weights=CATEGORY_WEIGHTS, k=1)[0]
    low, high = CATEGORIES[category]
    unit_price = round(random.uniform(low, high), 2)
    # 单价高的品类购买件数天然更少
    if unit_price > 500:
        quantity = random.choices([1, 2], weights=[0.9, 0.1], k=1)[0]
    else:
        quantity = random.choices([1, 2, 3, 4], weights=[0.62, 0.22, 0.11, 0.05], k=1)[0]
    channel = random.choices(CHANNELS, weights=CHANNEL_WEIGHTS, k=1)[0]
    region = random.choices(REGIONS, weights=REGION_WEIGHTS, k=1)[0]
    member = random.choices(MEMBER_LEVELS, weights=MEMBER_WEIGHTS, k=1)[0]
    amount = round(quantity * unit_price, 2)
    refund = 1 if random.random() < 0.075 else 0
    return {
        "order_id": f"YQ{d:%Y%m%d}{order_id:05d}",
        "order_date": d.isoformat(),
        "category": category,
        "channel": channel,
        "region": region,
        "member_level": member,
        "quantity": quantity,
        "unit_price": unit_price,
        "amount": amount,
        "refund_flag": refund,
    }


def build_clean_rows() -> pd.DataFrame:
    random.seed(20260101)
    rows = []
    seq = 1
    d = date(2026, 1, 1)
    while d <= date(2026, 9, 30):
        for _ in range(_daily_orders(d)):
            rows.append(_make_order(seq, d))
            seq += 1
        d += timedelta(days=1)
    return pd.DataFrame(rows)


def inject_dirty(df: pd.DataFrame) -> pd.DataFrame:
    """注入 5 类典型脏数据，每类都应在清洗环节被识别。"""
    rng = random.Random(7)
    dirty = df.copy()

    # 1) 关键字段缺失（24 行，每个关键字段各 3 行）
    cols_missing = ["category", "channel", "region", "quantity", "unit_price", "amount", "order_date", "member_level"]
    null_idx = rng.sample(list(dirty.index), len(cols_missing) * 3)
    for i, idx in enumerate(null_idx):
        dirty.loc[idx, cols_missing[i % len(cols_missing)]] = None

    # 2) 数值异常（24 行）：非正数量/金额、离谱大单、金额对不上
    bad_idx = rng.sample(list(dirty.index), 24)
    for k, idx in enumerate(bad_idx):
        variant = k % 8
        if variant == 0:
            dirty.loc[idx, "quantity"] = 0
        elif variant == 1:
            dirty.loc[idx, "quantity"] = -3
        elif variant == 2:
            dirty.loc[idx, "amount"] = -199.0
        elif variant == 3:
            dirty.loc[idx, "quantity"] = 999
        elif variant == 4:
            dirty.loc[idx, "amount"] = 1_000_000.0
        elif variant == 5:
            dirty.loc[idx, "unit_price"] = 0.0
        elif variant == 6:
            dirty.loc[idx, "quantity"] = 100
        else:
            dirty.loc[idx, "amount"] = 0.01

    # 3) 日期非法或超出统计区间（12 行）
    date_idx = rng.sample(list(dirty.index), 12)
    bad_dates = [
        "2026-13-45",
        "2026/09/31",
        "2025-11-20",
        "2026-10-08",
        "",
        "2026-02-30",
    ]
    for k, idx in enumerate(date_idx):
        dirty.loc[idx, "order_date"] = bad_dates[k % len(bad_dates)]

    # 4) 完全重复行（15 行，复制已有记录）
    dup_idx = rng.sample(list(dirty.index), 15)
    dirty = pd.concat([dirty, dirty.loc[dup_idx]], ignore_index=True)

    # 5) 重复订单号但内容不同（8 行，订单号撞号）
    id_idx = rng.sample(list(dirty.index), 8)
    for idx in id_idx[1:]:
        dirty.loc[idx, "order_id"] = dirty.loc[id_idx[0], "order_id"]

    dirty = dirty.sample(frac=1.0, random_state=11).reset_index(drop=True)
    return dirty


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    clean_base = build_clean_rows()
    raw = inject_dirty(clean_base)

    raw_path = DATA_DIR / "raw_orders.csv"
    raw.to_csv(raw_path, index=False, encoding="utf-8-sig")

    print(f"干净基准行数：{len(clean_base)}")
    print(f"注入后总行数：{len(raw)}（额外复制重复行 {len(raw) - len(clean_base)} 行）")
    print("注入内容：关键字段缺失 24 处、数值异常 24 处、日期非法 12 处、完全重复 15 行、订单号撞号 8 行")
    print(f"已写出：{raw_path}")
    print(f"字段：{', '.join(raw.columns)}")


if __name__ == "__main__":
    main()
