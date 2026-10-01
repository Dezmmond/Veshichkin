from pydantic import BaseModel, ConfigDict


class OrderedReferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    sort_order: int


class ConditionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    rank: int
    description: str | None
