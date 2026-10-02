from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from veshichkin.db.models import Climate, Condition, Purpose


def list_purposes(session: Session) -> Sequence[Purpose]:
    return session.scalars(
        select(Purpose).order_by(Purpose.sort_order, Purpose.name, Purpose.id)
    ).all()


def list_conditions(session: Session) -> Sequence[Condition]:
    return session.scalars(
        select(Condition).order_by(Condition.rank, Condition.name, Condition.id)
    ).all()


def list_climates(session: Session) -> Sequence[Climate]:
    return session.scalars(
        select(Climate).order_by(Climate.sort_order, Climate.name, Climate.id)
    ).all()
