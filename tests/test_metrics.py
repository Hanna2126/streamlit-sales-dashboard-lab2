# -*- coding: utf-8 -*-
"""统计口径单元测试。"""
import pandas as pd
import pytest

from src.metrics import (
    build_text_report,
    category_summary,
    channel_share,
    filter_orders,
    kpi_summary,
    mom_growth,
    monthly_trend,
    region_rank,
    target_achievement,
)


@pytest.fixture()
def sample() -> pd.DataFrame:
    rows = [
        dict(order_id="1", order_date="2026-01-05", category="数码配件", channel="自营商城", region="华东",
             member_level="普通会员", quantity=1, unit_price=100.0, amount=100.0, refund_flag=0, refund_amount=0.0, month="2026-01"),
        dict(order_id="2", order_date="2026-01-20", category="家居日用", channel="小程序", region="华南",
             member_level="银卡会员", quantity=2, unit_price=50.0, amount=100.0, refund_flag=1, refund_amount=100.0, month="2026-01"),
        dict(order_id="3", order_date="2026-02-08", category="数码配件", channel="自营商城", region="华东",
             member_level="金卡会员", quantity=3, unit_price=100.0, amount=300.0, refund_flag=0, refund_amount=0.0, month="2026-02"),
    ]
    df = pd.DataFrame(rows)
    df["order_date"] = pd.to_datetime(df["order_date"])
    return df


def test_filter_orders_by_dimension(sample):
    out = filter_orders(sample, categories=["数码配件"], channels=["自营商城"])
    assert len(out) == 2
    assert set(out["region"]) == {"华东"}


def test_filter_orders_by_date(sample):
    out = filter_orders(sample, start="2026-02-01", end="2026-02-28")
    assert len(out) == 1
    assert out.iloc[0]["order_id"] == "3"


def test_kpi_summary(sample):
    k = kpi_summary(sample)
    assert k["total_amount"] == pytest.approx(500.0)
    assert k["orders"] == 3
    assert k["avg_order_value"] == pytest.approx(166.67, abs=0.01)
    assert k["refund_rate"] == pytest.approx(1 / 3, abs=1e-4)
    assert k["refund_amount"] == pytest.approx(100.0)


def test_monthly_trend(sample):
    t = monthly_trend(sample)
    assert list(t["month"]) == ["2026-01", "2026-02"]
    assert list(t["amount"]) == [200.0, 300.0]


def test_mom_growth(sample):
    assert mom_growth(sample) == pytest.approx(0.5)


def test_category_share_sums_to_one(sample):
    cats = category_summary(sample)
    assert cats["share"].sum() == pytest.approx(1.0)
    assert cats["amount"].sum() == pytest.approx(500.0)
    # 升序排列，利润最大的品类在最后一行
    assert cats.iloc[-1]["category"] == "数码配件"


def test_channel_share(sample):
    ch = channel_share(sample)
    assert ch["share"].sum() == pytest.approx(1.0)
    assert ch.iloc[0]["channel"] == "自营商城"


def test_region_rank_top_n(sample):
    ranks = region_rank(sample, top_n=1)
    assert len(ranks) == 1
    assert ranks.iloc[0]["region"] == "华东"


def test_target_achievement(sample):
    t = target_achievement(sample, 400)
    assert t["month"] == "2026-02"
    assert t["rate"] == pytest.approx(0.75)


def test_text_report_contains_key_sections(sample):
    text = build_text_report(sample, kpi_summary(sample), target_achievement(sample, 400))
    assert "# 云栖优选销售看板 · 数据摘要" in text
    assert "## 月度趋势" in text
    assert "## 地区 TOP5" in text
    assert "500.00" in text
