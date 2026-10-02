from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator

Measurement = Annotated[Decimal, Field(gt=0, le=Decimal("9999.99"), allow_inf_nan=False)]
MEASUREMENT_FIELDS = (
    "height_cm",
    "weight_kg",
    "chest_cm",
    "waist_cm",
    "hips_cm",
    "inseam_cm",
    "foot_length_cm",
)


class MeasurementProfilePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    height_cm: Measurement | None = None
    weight_kg: Measurement | None = None
    chest_cm: Measurement | None = None
    waist_cm: Measurement | None = None
    hips_cm: Measurement | None = None
    inseam_cm: Measurement | None = None
    foot_length_cm: Measurement | None = None
    extra_measurements: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator(*MEASUREMENT_FIELDS, mode="before")
    @classmethod
    def reject_bool(cls, value: object) -> object:
        if isinstance(value, bool):
            raise ValueError("measurement cannot be boolean")
        return value

    @field_validator(*MEASUREMENT_FIELDS)
    @classmethod
    def round_measurement(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return None
        rounded = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if rounded <= 0:
            raise ValueError("measurement must remain positive at two decimal places")
        return rounded


class MeasurementProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    height_cm: Decimal | None
    weight_kg: Decimal | None
    chest_cm: Decimal | None
    waist_cm: Decimal | None
    hips_cm: Decimal | None
    inseam_cm: Decimal | None
    foot_length_cm: Decimal | None
    extra_measurements: dict[str, JsonValue]
    updated_at: datetime
