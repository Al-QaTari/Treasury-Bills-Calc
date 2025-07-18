from pydantic import BaseModel, Field, PositiveFloat, NonNegativeFloat, field_validator


class PrimaryYieldInput(BaseModel):
    """
    نموذج يمثل المدخلات اللازمة لحاسبة العائد الأساسية.
    Pydantic سيتحقق من صحة هذه الشروط تلقائياً.
    """

    face_value: PositiveFloat  # يجب أن يكون رقماً عشرياً موجباً
    yield_rate: PositiveFloat
    tenor: int = Field(gt=0)  # يجب أن يكون رقماً صحيحاً أكبر من صفر
    tax_rate: float = Field(ge=0, le=100)  # يجب أن يكون رقماً بين 0 و 100


class PrimaryYieldResult(BaseModel):
    """
    نموذج يمثل مخرجات حاسبة العائد الأساسية.
    """

    purchase_price: PositiveFloat
    gross_return: NonNegativeFloat  # يمكن أن يكون صفراً
    tax_amount: NonNegativeFloat
    net_return: float  # يمكن أن يكون الربح الصافي سالباً في حالات نادرة
    total_payout: PositiveFloat
    real_profit_percentage: float


class SecondarySaleInput(BaseModel):
    """
    نموذج يمثل المدخلات اللازمة لحاسبة البيع الثانوي.
    """

    face_value: PositiveFloat
    original_yield: PositiveFloat
    original_tenor: int = Field(gt=0)
    holding_days: int = Field(gt=0)
    secondary_yield: PositiveFloat
    tax_rate: float = Field(ge=0, le=100)

    @field_validator("holding_days")
    def validate_holding_days(cls, value, info):
        tenor = info.data.get("original_tenor")
        if tenor is not None and (value <= 0 or value >= tenor):
            raise ValueError(
                "أيام الاحتفاظ يجب أن تكون أكبر من صفر وأقل من أجل الإذن الأصلي."
            )
        return value


class SecondarySaleResult(BaseModel):
    """
    نموذج يمثل مخرجات حاسبة البيع الثانوي.
    """

    original_purchase_price: PositiveFloat
    sale_price: PositiveFloat
    gross_profit: float  # الربح الإجمالي يمكن أن يكون سالباً (خسارة)
    tax_amount: NonNegativeFloat
    net_profit: float
    period_yield: float
