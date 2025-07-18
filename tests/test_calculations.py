import sys
import os
import pytest
from pydantic import ValidationError

# إصلاح مسار الاستيراد
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from treasury_core.calculations import calculate_primary_yield, analyze_secondary_sale
from treasury_core.models import PrimaryYieldInput, SecondarySaleInput


# -------------------------------
# 📌 اختبارات العائد الأساسي
# -------------------------------


class TestPrimaryYield:
    """مجموعة اختبارات حاسبة العائد الأساسي"""

    @pytest.fixture
    def valid_input(self):
        return {
            "face_value": 100_000.0,
            "yield_rate": 25.0,
            "tenor": 364,
            "tax_rate": 20.0,
        }

    def test_logic_is_self_consistent(self, valid_input):
        """🧪 يتحقق من صحة الترابط الداخلي لنتائج حاسبة العائد الأساسي"""
        inputs = PrimaryYieldInput(**valid_input)
        results = calculate_primary_yield(inputs)

        # اختبار العلاقات الرياضية الأساسية
        assert results.purchase_price + results.gross_return == pytest.approx(
            valid_input["face_value"]
        )
        assert results.net_return == pytest.approx(
            results.gross_return - results.tax_amount
        )
        assert results.tax_amount == pytest.approx(
            results.gross_return * (valid_input["tax_rate"] / 100)
        )
        assert results.total_payout == pytest.approx(valid_input["face_value"])

    def test_edge_cases(self):
        """🧪 يتحقق من الحالات الحدية والقيم الصغيرة"""
        test_cases = [
            {"face_value": 1.0, "yield_rate": 0.1, "tenor": 1, "tax_rate": 0.0},
            {
                "face_value": 1_000_000.0,
                "yield_rate": 30.0,
                "tenor": 365,
                "tax_rate": 25.0,
            },
            {"face_value": 5000.0, "yield_rate": 15.0, "tenor": 91, "tax_rate": 10.0},
        ]

        for case in test_cases:
            inputs = PrimaryYieldInput(**case)
            results = calculate_primary_yield(inputs)
            assert results.purchase_price < inputs.face_value
            assert results.total_payout == inputs.face_value

    def test_invalid_input(self):
        """🧪 يتحقق من رفض المدخلات غير الصالحة"""
        invalid_inputs = [
            {
                "face_value": 0,
                "yield_rate": 25.0,
                "tenor": 364,
                "tax_rate": 20.0,
            },  # قيمة اسمية صفر
            {
                "face_value": 100_000,
                "yield_rate": 0,
                "tenor": 364,
                "tax_rate": 20.0,
            },  # عائد صفر
            {
                "face_value": 100_000,
                "yield_rate": 25.0,
                "tenor": 0,
                "tax_rate": 20.0,
            },  # مدة صفر
            {
                "face_value": 100_000,
                "yield_rate": 25.0,
                "tenor": 364,
                "tax_rate": -5.0,
            },  # ضريبة سالبة
            {
                "face_value": 100_000,
                "yield_rate": 25.0,
                "tenor": 364,
                "tax_rate": 150.0,
            },  # ضريبة > 100
        ]

        for kwargs in invalid_inputs:
            with pytest.raises(ValidationError):
                PrimaryYieldInput(**kwargs)

    def test_precision_calculation(self, valid_input):
        """🧪 يتحقق من دقة الحسابات باستخدام قيم عشرية"""
        inputs = PrimaryYieldInput(**valid_input)
        results1 = calculate_primary_yield(inputs)

        # تغيير طفيف في المدخلات
        valid_input["yield_rate"] = 25.01
        results2 = calculate_primary_yield(PrimaryYieldInput(**valid_input))

        # التأكد من أن النتائج مختلفة
        assert results1.purchase_price != results2.purchase_price


# -------------------------------
# 📌 اختبارات البيع الثانوي
# -------------------------------


class TestSecondarySale:
    """مجموعة اختبارات حاسبة البيع الثانوي"""

    @pytest.fixture
    def valid_input(self):
        return {
            "face_value": 100_000,
            "original_yield": 25.0,
            "original_tenor": 364,
            "holding_days": 90,
            "secondary_yield": 23.0,
            "tax_rate": 20.0,
        }

    def test_profit_scenario(self, valid_input):
        """🧪 يتحقق من الحسابات في حالة تحقيق ربح"""
        inputs = SecondarySaleInput(**valid_input)
        results = analyze_secondary_sale(inputs)

        assert results.sale_price > results.original_purchase_price
        assert results.gross_profit > 0
        assert results.tax_amount > 0
        assert results.net_profit == pytest.approx(
            results.gross_profit - results.tax_amount
        )

    def test_loss_scenario(self):
        """🧪 يتحقق من الحسابات في حالة الخسارة"""
        inputs = SecondarySaleInput(
            face_value=100_000,
            original_yield=25.0,
            original_tenor=364,
            holding_days=90,
            secondary_yield=35.0,
            tax_rate=20.0,
        )
        results = analyze_secondary_sale(inputs)

        assert results.sale_price < results.original_purchase_price
        assert results.gross_profit < 0
        assert results.tax_amount == 0
        assert results.net_profit == pytest.approx(results.gross_profit)

    def test_invalid_holding_days(self, valid_input):
        """🧪 يتحقق من رفض أيام الاحتفاظ غير المنطقية"""
        invalid_days = [0, 364, 400, -10]

        for days in invalid_days:
            with pytest.raises(ValidationError, match="holding_days"):
                SecondarySaleInput(**{**valid_input, "holding_days": days})

    def test_edge_cases(self):
        """🧪 يتحقق من الحالات الحدية للبيع الثانوي"""
        test_cases = [
            {"holding_days": 1, "secondary_yield": 1.0},  # بيع مبكر جدًا
            {"holding_days": 363, "secondary_yield": 25.0},  # بيع قبل يوم واحد
            {"holding_days": 180, "secondary_yield": 0.1},  # عائد ثانوي منخفض
            {"holding_days": 180, "secondary_yield": 50.0},  # عائد ثانوي مرتفع
        ]

        base_input = {
            "face_value": 100_000,
            "original_yield": 25.0,
            "original_tenor": 364,
            "tax_rate": 20.0,
        }

        for case in test_cases:
            inputs = SecondarySaleInput(**{**base_input, **case})
            results = analyze_secondary_sale(inputs)
            assert results.period_yield != 0  # التأكد من وجود نتيجة

    def test_tax_calculation(self, valid_input):
        """🧪 يتحقق من صحة حساب الضريبة في مختلف السيناريوهات"""
        # حالة بدون ضريبة (خسارة)
        inputs = SecondarySaleInput(**{**valid_input, "secondary_yield": 35.0})
        results = analyze_secondary_sale(inputs)
        assert results.tax_amount == 0

        # حالة بضريبة صفرية
        inputs = SecondarySaleInput(**{**valid_input, "tax_rate": 0.0})
        results = analyze_secondary_sale(inputs)
        assert results.tax_amount == 0
        assert results.net_profit == pytest.approx(results.gross_profit)

        # حالة بضريبة كاملة
        inputs = SecondarySaleInput(**{**valid_input, "tax_rate": 100.0})
        results = analyze_secondary_sale(inputs)
        assert results.tax_amount == pytest.approx(results.gross_profit)
        assert results.net_profit == 0
