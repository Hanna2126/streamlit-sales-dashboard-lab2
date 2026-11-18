# -*- coding: utf-8 -*-
"""订单数据预处理：清洗脏数据并输出可直接用于可视化的宽表。

清洗规则（顺序固定，便于复现与讲解）：
    1. 日期：无法解析、为空、或将 2026-02-30 这类不存在日期归一后仍非法 → 剔除；
       统计区间固定为 2026-01-01 ~ 2026-09-30，区间外剔除。
    2. 关键字段缺失：category / channel / region / member_level / quantity /
       unit_price / amount 任一为空 → 整行剔除（不猜、不补）。
    3. 数值非法：quantity <= 0 或 quantity > 20（明显异常的大单）、unit_price <= 0、
       amount <= 0 → 剔除。
    4. 金额一致性：amount 与 quantity * unit_price 偏差超过 5% → 视为脏数据剔除，
       同时把保留行的 amount 按 quantity * unit_price 重算，保留两位小数。
    5. 去重：先删完全重复行（保留首次出现），再按 order_id 去重（保留首次出现）。

顺序不能随意调整：先剔非法值再对账金额，否则被污染的 amount 会把一致性校验带偏；
先去重再算金额，会让重复行的处理结果不一致。
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

DATE_START = "2026-01-01"
DATE_END = "2026-09-30"

KEY_FIELDS = [
    "order_date",
    "category",
    "channel",
    "region",
    "member_level",
    "quantity",
    "unit_price",
    "amount",
]
NUMERIC_FIELDS = ["quantity", "unit_price", "amount", "refund_flag"]
TEXT_FIELDS = ["order_id", "category", "channel", "region", "member_level"]

MAX_QUANTITY = 20           # 单笔订单最多 20 件，超过视为异常
AMOUNT_TOLERANCE = 0.05     # 金额与「数量×单价」的允许偏差（5%）


def parse_orders(raw: pd.DataFrame) -> pd.DataFrame:
    """统一列类型：日期转 datetime（非法置空），数值转 float，文本去首尾空格。"""
    df = raw.copy()
    for col in TEXT_FIELDS:
        if col in df.columns:
            df[col] = df[col].astype("object").map(
                lambda v: v.strip() if isinstance(v, str) else v
            )
    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce", format="mixed")
    for col in NUMERIC_FIELDS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def clean_orders(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """执行完整清洗流程，返回清洗后数据和逐步骤统计。"""
    df = parse_orders(raw)
    total_in = len(df)
    steps: list[dict] = []

    def drop(mask: pd.Series, label: str, detail: str) -> None:
        nonlocal df
        removed = int(mask.sum())
        df = df[~mask].copy()
        steps.append({"step": label, "detail": detail, "removed": removed, "remain": len(df)})

    # 1. 日期
    bad_date = df["order_date"].isna()
    drop(bad_date, "日期非法", "无法解析 / 不存在日期（如 2026-02-30、2026/09/31）")
    out_range = (df["order_date"] < pd.Timestamp(DATE_START)) | (df["order_date"] > pd.Timestamp(DATE_END))
    drop(out_range, "日期超区间", f"统计区间外：{DATE_START} ~ {DATE_END}")

    # 2. 关键字段缺失
    missing = df[KEY_FIELDS].isna().any(axis=1)
    drop(missing, "关键字段缺失", " / ".join(KEY_FIELDS) + " 任一为空即整行剔除")

    # 3. 数值非法
    bad_qty = (df["quantity"] <= 0) | (df["quantity"] > MAX_QUANTITY)
    drop(bad_qty, "数量非法", f"quantity <= 0 或 > {MAX_QUANTITY}")
    bad_price = df["unit_price"] <= 0
    drop(bad_price, "单价非法", "unit_price <= 0")
    bad_amount = df["amount"] <= 0
    drop(bad_amount, "金额非法", "amount <= 0")

    # 4. 金额一致性
    expect = (df["quantity"] * df["unit_price"]).round(2)
    diff_ratio = (df["amount"] - expect).abs() / expect.replace(0, pd.NA)
    inconsistent = diff_ratio.fillna(1.0) > AMOUNT_TOLERANCE
    drop(inconsistent, "金额不一致", f"amount 与 数量×单价 偏差 > {AMOUNT_TOLERANCE:.0%}")

    # 5. 去重
    full_dup = df.duplicated(keep="first")
    drop(full_dup, "完全重复行", "全字段一致的重复，保留首次出现")
    id_dup = df.duplicated(subset=["order_id"], keep="first")
    drop(id_dup, "订单号重复", "订单号相同，保留首次出现")

    # 收尾：重算金额、补维度列
    df["amount"] = (df["quantity"] * df["unit_price"]).round(2)
    df["refund_flag"] = df["refund_flag"].fillna(0).astype(int)
    df["order_date"] = pd.to_datetime(df["order_date"])
    df["month"] = df["order_date"].dt.strftime("%Y-%m")
    df["refund_amount"] = (df["amount"] * df["refund_flag"]).round(2)
    df = df.sort_values("order_date").reset_index(drop=True)

    report = {
        "rows_in": total_in,
        "rows_out": len(df),
        "rows_removed": total_in - len(df),
        "dirty_ratio": round((total_in - len(df)) / total_in, 4) if total_in else 0.0,
        "steps": steps,
        "total_amount": round(float(df["amount"].sum()), 2),
        "orders": int(len(df)),
        "avg_order_value": round(float(df["amount"].mean()), 2) if len(df) else 0.0,
        "refund_rate": round(float(df["refund_flag"].mean()), 4) if len(df) else 0.0,
        "date_range": [str(df["order_date"].min().date()), str(df["order_date"].max().date())] if len(df) else [],
        "rules": {
            "max_quantity": MAX_QUANTITY,
            "amount_tolerance": AMOUNT_TOLERANCE,
            "date_range": [DATE_START, DATE_END],
        },
    }
    return df, report


def main() -> None:
    raw_path = DATA_DIR / "raw_orders.csv"
    if not raw_path.exists():
        raise SystemExit(f"未找到原始数据：{raw_path}，请先运行 data/generate_dataset.py")

    raw = pd.read_csv(raw_path, encoding="utf-8-sig")
    clean, report = clean_orders(raw)

    clean_path = DATA_DIR / "orders_clean.csv"
    clean.to_csv(clean_path, index=False, encoding="utf-8-sig")
    (DATA_DIR / "clean_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"原始行数：{report['rows_in']}")
    print("清洗过程：")
    for s in report["steps"]:
        print(f"  - {s['step']:<8} 剔除 {s['removed']:>3} 行，剩余 {s['remain']:>4} 行  ({s['detail']})")
    print(f"清洗后行数：{report['rows_out']}，脏数据占比 {report['dirty_ratio']:.2%}")
    print(f"销售额合计：{report['total_amount']:,.2f} 元")
    print(f"订单数：{report['orders']}，客单价：{report['avg_order_value']:,.2f} 元")
    print(f"退款率：{report['refund_rate']:.2%}")
    print(f"日期区间：{report['date_range'][0]} ~ {report['date_range'][1]}")
    print(f"已写出：{clean_path}")


if __name__ == "__main__":
    main()
