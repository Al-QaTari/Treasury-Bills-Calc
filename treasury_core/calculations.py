import logging
import constants as C
from .models import (
    PrimaryYieldInput,
    PrimaryYieldResult,
    SecondarySaleInput,
    SecondarySaleResult,
)
from pydantic import ValidationError
from decimal import Decimal, getcontext

# تهيئة دقة الأرقام العشرية
getcontext().prec = 10

logger = logging.getLogger(__name__)


def calculate_primary_yield(
    inputs: PrimaryYieldInput,
) -> PrimaryYieldResult:
    """
    يحسب عوائد الاستثمار في أذون الخزانة عند الشراء من السوق الأولي.
    """
    try:
        logger.debug(f"بدء حساب العائد الأساسي بالبيانات: {inputs.model_dump()}")

        # التحويل إلى Decimal للحسابات الدقيقة
        face_value = Decimal(str(inputs.face_value))
        yield_rate = Decimal(str(inputs.yield_rate))
        tenor = Decimal(str(inputs.tenor))
        tax_rate = Decimal(str(inputs.tax_rate))

        # التحقق من القيم الأساسية
        if yield_rate <= 0:
            raise ValueError("يجب أن يكون معدل العائد رقمًا موجبًا")
        if tenor <= 0:
            raise ValueError("يجب أن تكون مدة الإذن أكبر من الصفر")

        # حساب سعر الشراء
        denominator = Decimal("1") + (
            yield_rate / Decimal("100") * tenor / Decimal(str(C.DAYS_IN_YEAR))
        )

        if denominator <= 0:
            raise ValueError("قيمة المقام غير صالحة في حساب سعر الشراء")

        purchase_price = face_value / denominator
        gross_return = face_value - purchase_price
        tax_amount = gross_return * (tax_rate / Decimal("100"))
        net_return = gross_return - tax_amount

        real_profit_percentage = (
            (net_return / purchase_price) * Decimal("100")
            if purchase_price > Decimal("0")
            else Decimal("0")
        )

        # تحويل النتائج إلى float للإرجاع
        result = PrimaryYieldResult(
            purchase_price=float(purchase_price),
            gross_return=float(gross_return),
            tax_amount=float(tax_amount),
            net_return=float(net_return),
            total_payout=float(face_value),
            real_profit_percentage=float(real_profit_percentage),
        )

        logger.info(
            f"تم حساب العائد الأساسي بنجاح. صافي الربح: {result.net_return:.2f}"
        )
        return result

    except ZeroDivisionError:
        error_msg = "خطأ في الحساب: قسمة على صفر"
        logger.error(error_msg)
        raise ValueError(error_msg)
    except ValidationError as e:
        logger.error(f"خطأ في التحقق من صحة المدخلات: {e}")
        raise
    except ValueError as e:
        logger.error(f"خطأ في القيم المدخلة: {str(e)}")
        raise
    except Exception as e:
        error_msg = f"حدث خطأ غير متوقع أثناء حساب العائد الأساسي: {str(e)}"
        logger.error(error_msg)
        raise ValueError(error_msg)


def analyze_secondary_sale(
    inputs: SecondarySaleInput,
) -> SecondarySaleResult:
    """
    يحلل نتيجة بيع أذون الخزانة في السوق الثانوي.
    """
    try:
        logger.debug(f"بدء تحليل البيع الثانوي بالبيانات: {inputs.model_dump()}")

        # التحويل إلى Decimal للحسابات الدقيقة
        face_value = Decimal(str(inputs.face_value))
        original_yield = Decimal(str(inputs.original_yield))
        original_tenor = Decimal(str(inputs.original_tenor))
        holding_days = Decimal(str(inputs.holding_days))
        secondary_yield = Decimal(str(inputs.secondary_yield))
        tax_rate = Decimal(str(inputs.tax_rate))

        # التحقق من القيم الأساسية
        if original_yield <= 0 or secondary_yield <= 0:
            raise ValueError("يجب أن تكون معدلات العائد أرقامًا موجبة")

        if holding_days <= 0 or holding_days >= original_tenor:
            raise ValueError("أيام الاحتفاظ يجب أن تكون بين 1 وأقل من المدة الأصلية")

        # حساب سعر الشراء الأصلي
        original_denominator = Decimal("1") + (
            original_yield
            / Decimal("100")
            * original_tenor
            / Decimal(str(C.DAYS_IN_YEAR))
        )

        if original_denominator <= 0:
            raise ValueError("قيمة المقام غير صالحة في حساب السعر الأصلي")

        original_purchase_price = face_value / original_denominator

        # حساب سعر البيع الثانوي
        remaining_days = original_tenor - holding_days
        secondary_denominator = Decimal("1") + (
            secondary_yield
            / Decimal("100")
            * remaining_days
            / Decimal(str(C.DAYS_IN_YEAR))
        )

        if secondary_denominator <= 0:
            raise ValueError("قيمة المقام غير صالحة في حساب السعر الثانوي")

        sale_price = face_value / secondary_denominator

        # حساب الأرباح والضرائب
        gross_profit = sale_price - original_purchase_price
        tax_amount = max(Decimal("0"), gross_profit * (tax_rate / Decimal("100")))
        net_profit = gross_profit - tax_amount

        period_yield = (
            (net_profit / original_purchase_price) * Decimal("100")
            if original_purchase_price > Decimal("0")
            else Decimal("0")
        )

        # تحويل النتائج إلى float للإرجاع
        result = SecondarySaleResult(
            original_purchase_price=float(original_purchase_price),
            sale_price=float(sale_price),
            gross_profit=float(gross_profit),
            tax_amount=float(tax_amount),
            net_profit=float(net_profit),
            period_yield=float(period_yield),
        )

        logger.info(
            f"تم تحليل البيع الثانوي بنجاح. صافي الربح: {result.net_profit:.2f}"
        )
        return result

    except ZeroDivisionError:
        error_msg = "خطأ في الحساب: قسمة على صفر"
        logger.error(error_msg)
        raise ValueError(error_msg)
    except ValidationError as e:
        logger.error(f"خطأ في التحقق من صحة المدخلات: {e}")
        raise
    except ValueError as e:
        logger.error(f"خطأ في القيم المدخلة: {str(e)}")
        raise
    except Exception as e:
        error_msg = f"حدث خطأ غير متوقع أثناء تحليل البيع الثانوي: {str(e)}"
        logger.error(error_msg)
        raise ValueError(error_msg)
