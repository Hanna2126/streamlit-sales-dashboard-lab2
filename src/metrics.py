# -*- coding: utf-8 -*-
"""看板用到的统计口径，全部为纯函数，便于单测与复用。"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CLEAN_PATH = ROOT / "data" / "orders_clean.csv"


def load_orders(path: Path | str = CLEAN_PATH) -> pd.DataFrame:
    """读取清洗后的订单宽表。"""
    df = pd.read_csv(path, encoding="utf-8-sig", parse_dates=["order_date"])
    if "month" not in df.columns:
        df["month"] = df["order_date"].dt.strftime("%Y-%m")
    return df


def filter_orders(
    df: pd.DataFrame,
    start: str | pd.Timestamp | None = None,
    end: str | pd.Timestamp | None = None,
    categories: list[str] | None = None,
    channels: list[str] | None = None,
    regions: list[str] | None = None,
) -> pd.DataFrame:
    """按时间与分类维度筛选；传空列表表示该维度不过滤。"""
    mask = pd.Series(True, index=df.index)
    if start is not None:
        mask &= df["order_date"] >= pd.Timestamp(start)
    if end is not None:
        mask &= df["order_date"] <= pd.Timestamp(end)
    if categories:
        mask &= df["category"].isin(categories)
    if channels:
        mask &= df["channel"].isin(channels)
    if regions:
        mask &= df["region"].isin(regions)
    return df.loc[mask].copy()


def kpi_summary(df: pd.DataFrame) -> dict:
    """核心指标：总额、订单量、客单价、退款率、退款金额。"""
    orders = int(len(df))
    total = round(float(df["amount"].sum()), 2) if orders else 0.0
    refund_amount = round(float(df["refund_amount"].sum()), 2) if orders else 0.0
    return {
        "total_amount": total,
        "orders": orders,
        "avg_order_value": round(total / orders, 2) if orders else 0.0,
        "refund_amount": refund_amount,
        "refund_rate": round(float(df["refund_flag"].mean()), 4) if orders else 0.0,
    }


def monthly_trend(df: pd.DataFrame) -> pd.DataFrame:
    """按月汇总销售额与订单量，用于趋势折线图。"""
    if df.empty:
        return pd.DataFrame(columns=["month", "amount", "orders", "avg_order_value"])
    g = df.groupby("month").agg(
        amount=("amount", "sum"),
        orders=("order_id", "count"),
    )
    g["avg_order_value"] = (g["amount"] / g["orders"]).round(2)
    return g.round({"amount": 2}).reset_index()


def mom_growth(df: pd.DataFrame) -> float:
    """筛选区间内「最后一个完整月」相对上月的销售额环比。"""
    trend = monthly_trend(df)
    if len(trend) < 2:
        return 0.0
    prev = float(trend["amount"].iloc[-2])
    cur = float(trend["amount"].iloc[-1])
    if prev == 0:
        return 0.0
    return (cur - prev) / prev


def category_summary(df: pd.DataFrame) -> pd.DataFrame:
    """品类销售额、订单量与占比，用于条形图。"""
    if df.empty:
        return pd.DataFrame(columns=["category", "amount", "orders", "share"])
    g = df.groupby("category").agg(amount=("amount", "sum"), orders=("order_id", "count"))
    g["share"] = (g["amount"] / g["amount"].sum()).round(4)
    return g.round({"amount": 2}).sort_values("amount", ascending=True).reset_index()


def channel_share(df: pd.DataFrame) -> pd.DataFrame:
    """渠道销售额占比，用于环形图。"""
    if df.empty:
        return pd.DataFrame(columns=["channel", "amount", "share"])
    g = df.groupby("channel").agg(amount=("amount", "sum"))
    g["share"] = (g["amount"] / g["amount"].sum()).round(4)
    return g.round({"amount": 2}).sort_values("amount", ascending=False).reset_index()


def region_rank(df: pd.DataFrame, top_n: int = 5) -> pd.DataFrame:
    """地区排行榜。"""
    if df.empty:
        return pd.DataFrame(columns=["region", "amount", "orders", "share"])
    g = df.groupby("region").agg(amount=("amount", "sum"), orders=("order_id", "count"))
    g["share"] = (g["amount"] / g["amount"].sum()).round(4)
    return g.round({"amount": 2}).sort_values("amount", ascending=False).head(top_n).reset_index()


def member_summary(df: pd.DataFrame) -> pd.DataFrame:
    """会员等级维度：销售额与客单价。"""
    if df.empty:
        return pd.DataFrame(columns=["member_level", "amount", "orders", "avg_order_value"])
    g = df.groupby("member_level").agg(amount=("amount", "sum"), orders=("order_id", "count"))
    g["avg_order_value"] = (g["amount"] / g["orders"]).round(2)
    order = ["普通会员", "银卡会员", "金卡会员", "钻石会员"]
    g = g.reindex([m for m in order if m in g.index])
    return g.round({"amount": 2}).reset_index()


def category_month_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """品类 × 月份 的销售额矩阵，用于热力图。"""
    if df.empty:
        return pd.DataFrame()
    return df.pivot_table(index="category", columns="month", values="amount", aggfunc="sum").round(2)


def target_achievement(df: pd.DataFrame, monthly_target: float) -> dict:
    """最新月份的销售目标完成率，用于仪表盘。"""
    trend = monthly_trend(df)
    if trend.empty or monthly_target <= 0:
        return {"month": "-", "amount": 0.0, "target": float(monthly_target), "rate": 0.0}
    last = trend.iloc[-1]
    rate = float(last["amount"]) / float(monthly_target)
    return {
        "month": str(last["month"]),
        "amount": round(float(last["amount"]), 2),
        "target": float(monthly_target),
        "rate": round(rate, 4),
    }


def category_mom_drop(df: pd.DataFrame, threshold: float = -0.15) -> list[tuple[str, float]]:
    """找出最新月份环比下跌超过阈值的品类，用于预警。"""
    if df.empty:
        return []
    pivot = df.pivot_table(index="category", columns="month", values="amount", aggfunc="sum").fillna(0.0)
    if pivot.shape[1] < 2:
        return []
    prev, cur = pivot.iloc[:, -2], pivot.iloc[:, -1]
    drops = []
    for cat in pivot.index:
        if prev[cat] > 0:
            change = (cur[cat] - prev[cat]) / prev[cat]
            if change <= threshold:
                drops.append((str(cat), round(float(change), 4)))
    return sorted(drops, key=lambda x: x[1])


def build_text_report(df: pd.DataFrame, kpis: dict, target: dict) -> str:
    """一键生成 Markdown 数据报告（扩展4：从展示到分析输出）。"""
    trend = monthly_trend(df)
    cats = category_summary(df).sort_values("amount", ascending=False)
    regions = region_rank(df, top_n=5)
    lines = [
        "# 云栖优选销售看板 · 数据摘要",
        "",
        f"- 统计区间：{df['order_date'].min().date()} ~ {df['order_date'].max().date()}",
        f"- 销售额：{kpis['total_amount']:,.2f} 元；订单量：{kpis['orders']} 单；客单价：{kpis['avg_order_value']:,.2f} 元",
        f"- 退款金额：{kpis['refund_amount']:,.2f} 元；退款率：{kpis['refund_rate']:.2%}",
        f"- 最新月份 {target['month']} 完成率：{target['rate']:.2%}（目标 {target['target']:,.0f} 元）",
        "",
        "## 月度趋势",
        "",
    ]
    for _, row in trend.iterrows():
        lines.append(f"- {row['month']}：{row['amount']:,.2f} 元 / {int(row['orders'])} 单")
    lines += ["", "## 品类结构", ""]
    for _, row in cats.iterrows():
        lines.append(f"- {row['category']}：{row['amount']:,.2f} 元（占比 {row['share']:.2%}）")
    lines += ["", "## 地区 TOP5", ""]
    for i, (_, row) in enumerate(regions.iterrows(), 1):
        lines.append(f"{i}. {row['region']}：{row['amount']:,.2f} 元（占比 {row['share']:.2%}）")
    return "\n".join(lines)
