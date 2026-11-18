# -*- coding: utf-8 -*-
"""清洗规则单元测试：每一条规则都要有可复现的用例。"""
import pandas as pd
import pytest

from clean_data import clean_orders, MAX_QUANTITY


def make_row(**kwargs) -> dict:
    base = {
        "order_id": "YQ2026030100001",
        "order_date": "2026-03-01",
        "category": "数码配件",
        "channel": "自营商城",
        "region": "华东",
        "member_level": "普通会员",
        "quantity": 2,
        "unit_price": 100.0,
        "amount": 200.0,
        "refund_flag": 0,
    }
    base.update(kwargs)
    return base


def clean_one(**kwargs):
    return clean_orders(pd.DataFrame([make_row(**kwargs)]))


def test_valid_row_kept():
    df, report = clean_one()
    assert len(df) == 1
    assert report["rows_out"] == 1
    assert float(df.iloc[0]["amount"]) == 200.0


@pytest.mark.parametrize("field", ["category", "channel", "region", "member_level", "quantity", "unit_price", "amount", "order_date"])
def test_missing_key_field_dropped(field):
    df, report = clean_one(**{field: None})
    assert len(df) == 0
    assert report["rows_removed"] == 1


def test_invalid_calendar_date_dropped():
    df, _ = clean_one(order_date="2026-02-30")
    assert len(df) == 0


def test_out_of_range_date_dropped():
    df, _ = clean_one(order_date="2025-12-05")
    assert len(df) == 0


@pytest.mark.parametrize("qty", [0, -3, MAX_QUANTITY + 1])
def test_bad_quantity_dropped(qty):
    df, _ = clean_one(quantity=qty, amount=qty * 100.0)
    assert len(df) == 0


def test_zero_price_dropped():
    df, _ = clean_one(unit_price=0.0, amount=0.0)
    assert len(df) == 0


def test_negative_amount_dropped():
    df, _ = clean_one(amount=-199.0)
    assert len(df) == 0


def test_amount_inconsistent_dropped():
    df, _ = clean_one(amount=1000000.0)
    assert len(df) == 0


def test_amount_recalculated_to_two_decimals():
    df, _ = clean_one(quantity=3, unit_price=33.333, amount=99.999)
    assert len(df) == 1
    assert float(df.iloc[0]["amount"]) == round(3 * 33.333, 2)


def test_full_duplicate_rows_dropped():
    rows = pd.DataFrame([make_row(), make_row()])
    df, report = clean_orders(rows)
    assert len(df) == 1
    assert any(s["step"] == "完全重复行" and s["removed"] == 1 for s in report["steps"])


def test_same_order_id_dropped():
    rows = pd.DataFrame([
        make_row(order_id="YQ1", amount=200.0),
        make_row(order_id="YQ1", quantity=3, amount=300.0),
    ])
    df, report = clean_orders(rows)
    assert len(df) == 1
    assert any(s["step"] == "订单号重复" and s["removed"] == 1 for s in report["steps"])


def test_report_metrics_match_frame():
    rows = pd.DataFrame([
        make_row(order_id="A", quantity=1, unit_price=50.0, amount=50.0, refund_flag=1),
        make_row(order_id="B", quantity=2, unit_price=80.0, amount=160.0),
    ])
    df, report = clean_orders(rows)
    assert report["orders"] == 2
    assert report["total_amount"] == pytest.approx(210.0)
    assert report["avg_order_value"] == pytest.approx(105.0)
    assert report["refund_rate"] == pytest.approx(0.5)
    assert report["date_range"] == ["2026-03-01", "2026-03-01"]
