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
from utils import log_performance_metrics, safe_divide, validate_numeric_input

# تهيئة دقة الأرقام العشرية
getcontext().prec = 10

logger = logging.getLogger(__name__)


def calculate_primary_yield(
    inputs: PrimaryYieldInput,
) -> PrimaryYieldResult:
    """
    يحسب عوائد الاستثمار في أذون الخزانة عند الشراء من السوق الأولي.
    
    التحسينات الجديدة:
    - تحسين دقة الحسابات باستخدام Decimal
    - معالجة محسنة للأخطاء
    - إضافة مقاييس الأداء
    - تحسين التحقق من صحة المدخلات
    """
    start_time = log_performance_metrics.__globals__.get('time', lambda: 0)()
    
    try:
        logger.debug(f"بدء حساب العائد الأساسي بالبيانات: {inputs.model_dump()}")

        # التحقق من صحة المدخلات
        validated_inputs = _validate_primary_inputs(inputs)
        
        # التحويل إلى Decimal للحسابات الدقيقة
        face_value = Decimal(str(validated_inputs.face_value))
        yield_rate = Decimal(str(validated_inputs.yield_rate))
        tenor = Decimal(str(validated_inputs.tenor))
        tax_rate = Decimal(str(validated_inputs.tax_rate))

        # حساب سعر الشراء
        purchase_price = _calculate_purchase_price(face_value, yield_rate, tenor)
        
        # حساب الأرباح والضرائب
        gross_return = face_value - purchase_price
        tax_amount = gross_return * (tax_rate / Decimal("100"))
        net_return = gross_return - tax_amount

        # حساب النسبة الفعلية للربح
        real_profit_percentage = _calculate_real_profit_percentage(net_return, purchase_price)

        # تحويل النتائج إلى float للإرجاع
        result = PrimaryYieldResult(
            purchase_price=float(purchase_price),
            gross_return=float(gross_return),
            tax_amount=float(tax_amount),
            net_return=float(net_return),
            total_payout=float(face_value),
            real_profit_percentage=float(real_profit_percentage),
        )

        # تسجيل مقاييس الأداء
        log_performance_metrics(
            "calculate_primary_yield", 
            start_time, 
            {"face_value": float(face_value), "tenor": int(tenor)}
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


def _validate_primary_inputs(inputs: PrimaryYieldInput) -> PrimaryYieldInput:
    """
    التحقق من صحة مدخلات العائد الأساسي.
    
    Args:
        inputs: مدخلات العائد الأساسي
        
    Returns:
        المدخلات المحققة
    """
    try:
        # التحقق من القيم الأساسية
        if inputs.yield_rate <= 0:
            raise ValueError("يجب أن يكون معدل العائد رقمًا موجبًا")
        if inputs.tenor <= 0:
            raise ValueError("يجب أن تكون مدة الإذن أكبر من الصفر")
        if inputs.face_value <= 0:
            raise ValueError("يجب أن تكون القيمة الإسمية رقمًا موجبًا")
        if inputs.tax_rate < 0 or inputs.tax_rate > 100:
            raise ValueError("نسبة الضريبة يجب أن تكون بين 0 و 100")
            
        # التحقق من الحدود
        if inputs.face_value < C.MIN_T_BILL_AMOUNT:
            raise ValueError(f"القيمة الإسمية يجب أن تكون على الأقل {C.MIN_T_BILL_AMOUNT}")
        if inputs.face_value > C.MAX_T_BILL_AMOUNT:
            raise ValueError(f"القيمة الإسمية يجب أن تكون أقل من {C.MAX_T_BILL_AMOUNT}")
        if inputs.yield_rate > C.MAX_YIELD_RATE:
            raise ValueError(f"معدل العائد يجب أن يكون أقل من {C.MAX_YIELD_RATE}%")
        if inputs.tenor > C.MAX_TENOR_DAYS:
            raise ValueError(f"مدة الإذن يجب أن تكون أقل من {C.MAX_TENOR_DAYS} يوم")
            
        return inputs
        
    except Exception as e:
        logger.error(f"Error validating primary inputs: {e}", exc_info=True)
        raise


def _calculate_purchase_price(face_value: Decimal, yield_rate: Decimal, tenor: Decimal) -> Decimal:
    """
    حساب سعر الشراء الفعلي.
    
    Args:
        face_value: القيمة الإسمية
        yield_rate: معدل العائد
        tenor: مدة الإذن بالأيام
        
    Returns:
        سعر الشراء الفعلي
    """
    try:
        # حساب المقام
        denominator = Decimal("1") + (
            yield_rate / Decimal("100") * tenor / Decimal(str(C.DAYS_IN_YEAR))
        )

        if denominator <= 0:
            raise ValueError("قيمة المقام غير صالحة في حساب سعر الشراء")

        # حساب سعر الشراء
        purchase_price = face_value / denominator
        
        # التحقق من صحة النتيجة
        if purchase_price <= 0:
            raise ValueError("سعر الشراء يجب أن يكون رقمًا موجبًا")
        if purchase_price >= face_value:
            raise ValueError("سعر الشراء يجب أن يكون أقل من القيمة الإسمية")
            
        return purchase_price
        
    except Exception as e:
        logger.error(f"Error calculating purchase price: {e}", exc_info=True)
        raise


def _calculate_real_profit_percentage(net_return: Decimal, purchase_price: Decimal) -> Decimal:
    """
    حساب النسبة الفعلية للربح.
    
    Args:
        net_return: صافي الربح
        purchase_price: سعر الشراء
        
    Returns:
        النسبة الفعلية للربح
    """
    try:
        if purchase_price <= 0:
            return Decimal("0")
            
        real_profit_percentage = (net_return / purchase_price) * Decimal("100")
        return real_profit_percentage
        
    except Exception as e:
        logger.error(f"Error calculating real profit percentage: {e}", exc_info=True)
        return Decimal("0")


def analyze_secondary_sale(
    inputs: SecondarySaleInput,
) -> SecondarySaleResult:
    """
    يحلل نتيجة بيع أذون الخزانة في السوق الثانوي.
    
    التحسينات الجديدة:
    - تحسين دقة الحسابات
    - معالجة محسنة للأخطاء
    - إضافة مقاييس الأداء
    - تحسين التحقق من صحة المدخلات
    """
    start_time = log_performance_metrics.__globals__.get('time', lambda: 0)()
    
    try:
        logger.debug(f"بدء تحليل البيع الثانوي بالبيانات: {inputs.model_dump()}")

        # التحقق من صحة المدخلات
        validated_inputs = _validate_secondary_inputs(inputs)
        
        # التحويل إلى Decimal للحسابات الدقيقة
        face_value = Decimal(str(validated_inputs.face_value))
        original_yield = Decimal(str(validated_inputs.original_yield))
        original_tenor = Decimal(str(validated_inputs.original_tenor))
        holding_days = Decimal(str(validated_inputs.holding_days))
        secondary_yield = Decimal(str(validated_inputs.secondary_yield))
        tax_rate = Decimal(str(validated_inputs.tax_rate))

        # حساب سعر الشراء الأصلي
        original_purchase_price = _calculate_purchase_price(face_value, original_yield, original_tenor)

        # حساب سعر البيع الثانوي
        remaining_days = original_tenor - holding_days
        sale_price = _calculate_secondary_sale_price(face_value, secondary_yield, remaining_days)

        # حساب الأرباح والضرائب
        gross_profit = sale_price - original_purchase_price
        tax_amount = max(Decimal("0"), gross_profit * (tax_rate / Decimal("100")))
        net_profit = gross_profit - tax_amount

        # حساب عائد الفترة
        period_yield = _calculate_period_yield(net_profit, original_purchase_price)

        # تحويل النتائج إلى float للإرجاع
        result = SecondarySaleResult(
            original_purchase_price=float(original_purchase_price),
            sale_price=float(sale_price),
            gross_profit=float(gross_profit),
            tax_amount=float(tax_amount),
            net_profit=float(net_profit),
            period_yield=float(period_yield),
        )

        # تسجيل مقاييس الأداء
        log_performance_metrics(
            "analyze_secondary_sale", 
            start_time, 
            {"face_value": float(face_value), "holding_days": int(holding_days)}
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


def _validate_secondary_inputs(inputs: SecondarySaleInput) -> SecondarySaleInput:
    """
    التحقق من صحة مدخلات البيع الثانوي.
    
    Args:
        inputs: مدخلات البيع الثانوي
        
    Returns:
        المدخلات المحققة
    """
    try:
        # التحقق من القيم الأساسية
        if inputs.original_yield <= 0 or inputs.secondary_yield <= 0:
            raise ValueError("يجب أن تكون معدلات العائد أرقامًا موجبة")

        if inputs.holding_days <= 0 or inputs.holding_days >= inputs.original_tenor:
            raise ValueError("أيام الاحتفاظ يجب أن تكون بين 1 وأقل من المدة الأصلية")
            
        if inputs.face_value <= 0:
            raise ValueError("يجب أن تكون القيمة الإسمية رقمًا موجبًا")
            
        if inputs.tax_rate < 0 or inputs.tax_rate > 100:
            raise ValueError("نسبة الضريبة يجب أن تكون بين 0 و 100")
            
        # التحقق من الحدود
        if inputs.face_value < C.MIN_T_BILL_AMOUNT:
            raise ValueError(f"القيمة الإسمية يجب أن تكون على الأقل {C.MIN_T_BILL_AMOUNT}")
        if inputs.face_value > C.MAX_T_BILL_AMOUNT:
            raise ValueError(f"القيمة الإسمية يجب أن تكون أقل من {C.MAX_T_BILL_AMOUNT}")
        if inputs.original_yield > C.MAX_YIELD_RATE or inputs.secondary_yield > C.MAX_YIELD_RATE:
            raise ValueError(f"معدل العائد يجب أن يكون أقل من {C.MAX_YIELD_RATE}%")
        if inputs.original_tenor > C.MAX_TENOR_DAYS:
            raise ValueError(f"مدة الإذن يجب أن تكون أقل من {C.MAX_TENOR_DAYS} يوم")
            
        return inputs
        
    except Exception as e:
        logger.error(f"Error validating secondary inputs: {e}", exc_info=True)
        raise


def _calculate_secondary_sale_price(face_value: Decimal, secondary_yield: Decimal, remaining_days: Decimal) -> Decimal:
    """
    حساب سعر البيع الثانوي.
    
    Args:
        face_value: القيمة الإسمية
        secondary_yield: معدل العائد الثانوي
        remaining_days: الأيام المتبقية
        
    Returns:
        سعر البيع الثانوي
    """
    try:
        # حساب المقام
        secondary_denominator = Decimal("1") + (
            secondary_yield
            / Decimal("100")
            * remaining_days
            / Decimal(str(C.DAYS_IN_YEAR))
        )

        if secondary_denominator <= 0:
            raise ValueError("قيمة المقام غير صالحة في حساب السعر الثانوي")

        # حساب سعر البيع
        sale_price = face_value / secondary_denominator
        
        # التحقق من صحة النتيجة
        if sale_price <= 0:
            raise ValueError("سعر البيع يجب أن يكون رقمًا موجبًا")
        if sale_price >= face_value:
            raise ValueError("سعر البيع يجب أن يكون أقل من القيمة الإسمية")
            
        return sale_price
        
    except Exception as e:
        logger.error(f"Error calculating secondary sale price: {e}", exc_info=True)
        raise


def _calculate_period_yield(net_profit: Decimal, original_purchase_price: Decimal) -> Decimal:
    """
    حساب عائد الفترة.
    
    Args:
        net_profit: صافي الربح
        original_purchase_price: سعر الشراء الأصلي
        
    Returns:
        عائد الفترة
    """
    try:
        if original_purchase_price <= 0:
            return Decimal("0")
            
        period_yield = (net_profit / original_purchase_price) * Decimal("100")
        return period_yield
        
    except Exception as e:
        logger.error(f"Error calculating period yield: {e}", exc_info=True)
        return Decimal("0")


def calculate_effective_annual_rate(nominal_rate: float, compounding_periods: int = 1) -> float:
    """
    حساب المعدل السنوي الفعلي.
    
    Args:
        nominal_rate: المعدل الاسمي
        compounding_periods: عدد مرات التركيب في السنة
        
    Returns:
        المعدل السنوي الفعلي
    """
    try:
        if nominal_rate <= 0 or compounding_periods <= 0:
            return 0.0
            
        effective_rate = ((1 + nominal_rate / (100 * compounding_periods)) ** compounding_periods - 1) * 100
        return effective_rate
        
    except Exception as e:
        logger.error(f"Error calculating effective annual rate: {e}", exc_info=True)
        return 0.0


def calculate_present_value(future_value: float, rate: float, periods: int) -> float:
    """
    حساب القيمة الحالية.
    
    Args:
        future_value: القيمة المستقبلية
        rate: معدل الخصم
        periods: عدد الفترات
        
    Returns:
        القيمة الحالية
    """
    try:
        if rate <= 0 or periods <= 0:
            return future_value
            
        present_value = future_value / ((1 + rate / 100) ** periods)
        return present_value
        
    except Exception as e:
        logger.error(f"Error calculating present value: {e}", exc_info=True)
        return future_value


def calculate_future_value(present_value: float, rate: float, periods: int) -> float:
    """
    حساب القيمة المستقبلية.
    
    Args:
        present_value: القيمة الحالية
        rate: معدل النمو
        periods: عدد الفترات
        
    Returns:
        القيمة المستقبلية
    """
    try:
        if rate <= 0 or periods <= 0:
            return present_value
            
        future_value = present_value * ((1 + rate / 100) ** periods)
        return future_value
        
    except Exception as e:
        logger.error(f"Error calculating future value: {e}", exc_info=True)
        return present_value


def calculate_duration(face_value: float, yield_rate: float, tenor: int) -> float:
    """
    حساب مدة ماكولي (Duration).
    
    Args:
        face_value: القيمة الإسمية
        yield_rate: معدل العائد
        tenor: مدة الإذن بالأيام
        
    Returns:
        مدة ماكولي
    """
    try:
        if yield_rate <= 0 or tenor <= 0:
            return 0.0
            
        # تحويل المدة إلى سنوات
        tenor_years = tenor / C.DAYS_IN_YEAR
        
        # حساب مدة ماكولي
        duration = tenor_years / (1 + yield_rate / 100)
        return duration
        
    except Exception as e:
        logger.error(f"Error calculating duration: {e}", exc_info=True)
        return 0.0


def calculate_convexity(face_value: float, yield_rate: float, tenor: int) -> float:
    """
    حساب التحدب (Convexity).
    
    Args:
        face_value: القيمة الإسمية
        yield_rate: معدل العائد
        tenor: مدة الإذن بالأيام
        
    Returns:
        التحدب
    """
    try:
        if yield_rate <= 0 or tenor <= 0:
            return 0.0
            
        # تحويل المدة إلى سنوات
        tenor_years = tenor / C.DAYS_IN_YEAR
        
        # حساب التحدب
        convexity = (tenor_years * (tenor_years + 1)) / ((1 + yield_rate / 100) ** 2)
        return convexity
        
    except Exception as e:
        logger.error(f"Error calculating convexity: {e}", exc_info=True)
        return 0.0


def calculate_price_sensitivity(face_value: float, yield_rate: float, tenor: int, yield_change: float) -> float:
    """
    حساب حساسية السعر للتغير في العائد.
    
    Args:
        face_value: القيمة الإسمية
        yield_rate: معدل العائد الحالي
        tenor: مدة الإذن بالأيام
        yield_change: التغير في العائد
        
    Returns:
        التغير في السعر
    """
    try:
        if yield_rate <= 0 or tenor <= 0:
            return 0.0
            
        # حساب مدة ماكولي والتحدب
        duration = calculate_duration(face_value, yield_rate, tenor)
        convexity = calculate_convexity(face_value, yield_rate, tenor)
        
        # حساب التغير في السعر
        price_change = -duration * yield_change + 0.5 * convexity * (yield_change ** 2)
        return price_change
        
    except Exception as e:
        logger.error(f"Error calculating price sensitivity: {e}", exc_info=True)
        return 0.0
