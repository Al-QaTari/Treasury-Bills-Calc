import logging
import constants as C
from .models import (
    PrimaryYieldInput,
    PrimaryYieldResult,
    SecondarySaleInput,
    SecondarySaleResult,
)

logger = logging.getLogger(__name__)


def calculate_primary_yield(
    inputs: PrimaryYieldInput,
) -> PrimaryYieldResult:
    """
    يحسب عوائد الاستثمار في أذون الخزانة عند الشراء من السوق الأولي.
    التحقق من صحة البيانات يتم تلقائياً باستخدام Pydantic.
    """
    logger.debug(f"Calculating primary yield with: {inputs.model_dump()}")

    purchase_price = inputs.face_value / (
        1 + (inputs.yield_rate / 100.0 * inputs.tenor / C.DAYS_IN_YEAR)
    )
    gross_return = inputs.face_value - purchase_price
    tax_amount = gross_return * (inputs.tax_rate / 100.0)
    net_return = gross_return - tax_amount
    real_profit_percentage = (
        (net_return / purchase_price) * 100 if purchase_price > 0 else 0
    )

    result = PrimaryYieldResult(
        purchase_price=purchase_price,
        gross_return=gross_return,
        tax_amount=tax_amount,
        net_return=net_return,
        total_payout=inputs.face_value,
        real_profit_percentage=real_profit_percentage,
    )

    logger.info(
        f"Primary yield calculated successfully. Net return: {result.net_return:.2f}"
    )
    return result


def analyze_secondary_sale(
    inputs: SecondarySaleInput,
) -> SecondarySaleResult:
    """
    يحلل نتيجة بيع أذون الخزانة في السوق الثانوي.
    التحقق من العلاقة بين الحقول يتم داخل نموذج Pydantic.
    """
    logger.debug(f"Analyzing secondary sale with inputs: {inputs.model_dump()}")

    original_purchase_price = inputs.face_value / (
        1 + (inputs.original_yield / 100.0 * inputs.original_tenor / C.DAYS_IN_YEAR)
    )
    remaining_days = inputs.original_tenor - inputs.holding_days
    sale_price = inputs.face_value / (
        1 + (inputs.secondary_yield / 100.0 * remaining_days / C.DAYS_IN_YEAR)
    )
    gross_profit = sale_price - original_purchase_price
    tax_amount = max(0, gross_profit * (inputs.tax_rate / 100.0))
    net_profit = gross_profit - tax_amount
    period_yield = (
        (net_profit / original_purchase_price) * 100
        if original_purchase_price > 0
        else 0
    )

    result = SecondarySaleResult(
        original_purchase_price=original_purchase_price,
        sale_price=sale_price,
        gross_profit=gross_profit,
        tax_amount=tax_amount,
        net_profit=net_profit,
        period_yield=period_yield,
    )

    logger.info(
        f"Secondary sale analyzed successfully. Net profit: {result.net_profit:.2f}"
    )
    return result
