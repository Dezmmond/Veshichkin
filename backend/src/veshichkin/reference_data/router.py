from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from veshichkin.db.models import Climate, Condition, Purpose
from veshichkin.db.session import get_session
from veshichkin.reference_data import operations
from veshichkin.reference_data.schemas import ConditionResponse, OrderedReferenceResponse

router = APIRouter(prefix="/reference", tags=["reference"])
DatabaseSession = Annotated[Session, Depends(get_session)]


@router.get("/purposes", response_model=list[OrderedReferenceResponse])
def list_purposes(session: DatabaseSession) -> Sequence[Purpose]:
    return operations.list_purposes(session)


@router.get("/conditions", response_model=list[ConditionResponse])
def list_conditions(session: DatabaseSession) -> Sequence[Condition]:
    return operations.list_conditions(session)


@router.get("/climates", response_model=list[OrderedReferenceResponse])
def list_climates(session: DatabaseSession) -> Sequence[Climate]:
    return operations.list_climates(session)
