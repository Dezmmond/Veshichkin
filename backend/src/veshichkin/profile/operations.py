from sqlalchemy.orm import Session

from veshichkin.db.models import MeasurementProfile
from veshichkin.profile.schemas import MeasurementProfilePatch


def get_measurements(session: Session) -> MeasurementProfile | None:
    return session.get(MeasurementProfile, 1)


def patch_measurements(session: Session, payload: MeasurementProfilePatch) -> MeasurementProfile:
    profile = get_measurements(session)
    if profile is None:
        profile = MeasurementProfile(id=1)
        session.add(profile)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    session.flush()
    return profile
