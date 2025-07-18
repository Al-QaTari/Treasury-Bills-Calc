import sys
import os
import pytest
from pydantic import ValidationError

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from treasury_core.calculations import calculate_primary_yield, analyze_secondary_sale
from treasury_core.models import PrimaryYieldInput, SecondarySaleInput


# -------------------------------
# 📌 اختبارات العائد الأساسي
# -------------------------------


def test_primary_yield_logic_is_self_consistent():
    """🧪 يتحقق من صحة الترابط الداخلي لنتائج حاسبة العائد الأساسي."""
    inputs = PrimaryYieldInput(
        face_value=100_000.0, yield_rate=25.0, tenor=364, tax_rate=20.0
    )
    results = calculate_primary_yield(inputs)

    assert results.purchase_price + results.gross_return == pytest.approx(100_000.0)
    assert results.net_return == pytest.approx(
        results.gross_return - results.tax_amount
    )
    assert results.tax_amount == pytest.approx(results.gross_return * 0.20)
    assert results.total_payout == pytest.approx(100_000.0)


def test_primary_yield_invalid_input():
    """🧪 يتحقق من رفض المدخلات غير الصالحة باستخدام Pydantic."""
    invalid_inputs = [
        dict(face_value=0, yield_rate=25.0, tenor=364, tax_rate=20.0),
        dict(face_value=100_000, yield_rate=0, tenor=364, tax_rate=20.0),
        dict(face_value=100_000, yield_rate=25.0, tenor=0, tax_rate=20.0),
        dict(face_value=100_000, yield_rate=25.0, tenor=364, tax_rate=150),
    ]

    for kwargs in invalid_inputs:
        with pytest.raises(ValidationError):
            PrimaryYieldInput(**kwargs)


# -------------------------------
# 📌 اختبارات البيع الثانوي
# -------------------------------


def test_secondary_sale_logic_with_profit():
    """🧪 يتحقق من الحسابات في حالة تحقيق ربح في البيع الثانوي."""
    inputs = SecondarySaleInput(
        face_value=100_000,
        original_yield=25.0,
        original_tenor=364,
        holding_days=90,
        secondary_yield=23.0,
        tax_rate=20.0,
    )
    results = analyze_secondary_sale(inputs)

    assert results.sale_price == pytest.approx(
        results.original_purchase_price + results.gross_profit
    )
    assert results.net_profit == pytest.approx(
        results.gross_profit - results.tax_amount
    )
    assert results.tax_amount > 0


def test_secondary_sale_logic_with_loss():
    """🧪 يتحقق من الحسابات في حالة الخسارة في البيع الثانوي."""
    inputs = SecondarySaleInput(
        face_value=100_000,
        original_yield=25.0,
        original_tenor=364,
        holding_days=90,
        secondary_yield=35.0,
        tax_rate=20.0,
    )
    results = analyze_secondary_sale(inputs)

    assert results.sale_price == pytest.approx(
        results.original_purchase_price + results.gross_profit
    )
    assert results.net_profit == pytest.approx(results.gross_profit)
    assert results.tax_amount == 0


def test_secondary_sale_invalid_days():
    """🧪 يتحقق من رفض الأيام غير المنطقية (صفر أو أكبر من الأجل)."""
    invalid_days = [0, 364, 400]

    for days in invalid_days:
        with pytest.raises(ValidationError, match="holding_days"):
            SecondarySaleInput(
                face_value=100_000,
                original_yield=25.0,
                original_tenor=364,
                holding_days=days,
                secondary_yield=28.0,
                tax_rate=20.0,
            )
