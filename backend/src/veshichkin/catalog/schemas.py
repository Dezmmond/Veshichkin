from datetime import datetime
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator, model_validator

Quantity = Annotated[int, Field(strict=True, ge=0, le=2147483647)]
TrackingMode = Literal["individual", "grouped"]
RelationId = Annotated[int, Field(strict=True, gt=0)]


class ItemScalars(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brand: str | None = None
    model: str | None = None
    color: str | None = None
    size: str | None = None
    material: str | None = None
    notes: str | None = None

    @field_validator("brand", "model", "color", "size", "material", "notes", mode="before")
    @classmethod
    def normalize_scalar(cls, value: object) -> object:
        return (value.strip() or None) if isinstance(value, str) else value

    @field_validator("name", mode="before", check_fields=False)
    @classmethod
    def trim_name(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class ItemRelations(ItemScalars):
    purpose_ids: list[RelationId] = Field(default_factory=list)
    climate_ids: list[RelationId] = Field(default_factory=list)

    @field_validator("purpose_ids", "climate_ids")
    @classmethod
    def reject_duplicates(cls, values: list[int]) -> list[int]:
        if len(values) != len(set(values)):
            raise ValueError("duplicate relation IDs are not allowed")
        return values


class ItemCreate(ItemRelations):
    name: str = Field(min_length=1)
    category_id: int
    condition_id: int
    tracking_mode: TrackingMode
    quantity: Quantity | None = None
    extra_attributes: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_quantity(self) -> Self:
        if self.quantity is None:
            if "quantity" in self.model_fields_set or self.tracking_mode == "grouped":
                raise ValueError("quantity is required and cannot be null")
            self.quantity = 1
        if self.tracking_mode == "individual" and self.quantity != 1:
            raise ValueError("individual quantity must be 1")
        return self


class ItemPatch(ItemRelations):
    name: str | None = Field(default=None, min_length=1)
    category_id: int | None = None
    condition_id: int | None = None
    quantity: Quantity | None = None
    extra_attributes: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def reject_null_values(self) -> Self:
        for field in ("name", "category_id", "condition_id", "quantity"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class ItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category_id: int
    name: str
    tracking_mode: TrackingMode
    quantity: int
    condition_id: int | None
    brand: str | None
    model: str | None
    color: str | None
    size: str | None
    material: str | None
    notes: str | None
    extra_attributes: dict[str, JsonValue]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    purpose_ids: list[int] = Field(default_factory=list)
    climate_ids: list[int] = Field(default_factory=list)
