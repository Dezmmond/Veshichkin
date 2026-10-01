from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1)
    parent_id: int | None = None
    sort_order: int = Field(default=0, ge=0)

    @field_validator("name", mode="before")
    @classmethod
    def trim_name(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class CategoryPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    parent_id: int | None = None
    sort_order: int | None = Field(default=None, ge=0)

    @field_validator("name", mode="before")
    @classmethod
    def trim_name(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def reject_null_values(self) -> Self:
        for field in ("name", "sort_order"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    parent_id: int | None
    sort_order: int


class CategoryTree(CategoryResponse):
    children: list["CategoryTree"] = Field(default_factory=list)
