from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    Numeric,
    SmallInteger,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from veshichkin.db.base import Base


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (
        CheckConstraint("sort_order >= 0", name="sort_order_nonnegative"),
        CheckConstraint("parent_id != id", name="parent_not_self"),
        CheckConstraint(
            "last_verification_state IN ('empty', 'nonempty')", name="verification_state_valid"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    parent_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("categories.id", ondelete="RESTRICT"), index=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, server_default="0")
    last_verification_state: Mapped[str | None] = mapped_column(Text)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Purpose(Base):
    __tablename__ = "purposes"
    __table_args__ = (CheckConstraint("sort_order >= 0", name="sort_order_nonnegative"),)

    id: Mapped[int] = mapped_column(SmallInteger, Identity(), primary_key=True)
    code: Mapped[str] = mapped_column(Text, unique=True)
    name: Mapped[str] = mapped_column(Text, unique=True)
    sort_order: Mapped[int] = mapped_column(Integer, server_default="0")


class Condition(Base):
    __tablename__ = "conditions"
    __table_args__ = (CheckConstraint("rank >= 0", name="rank_nonnegative"),)

    id: Mapped[int] = mapped_column(SmallInteger, Identity(), primary_key=True)
    code: Mapped[str] = mapped_column(Text, unique=True)
    name: Mapped[str] = mapped_column(Text, unique=True)
    rank: Mapped[int] = mapped_column(Integer, unique=True)
    description: Mapped[str | None] = mapped_column(Text)


class Climate(Base):
    __tablename__ = "climates"
    __table_args__ = (CheckConstraint("sort_order >= 0", name="sort_order_nonnegative"),)

    id: Mapped[int] = mapped_column(SmallInteger, Identity(), primary_key=True)
    code: Mapped[str] = mapped_column(Text, unique=True)
    name: Mapped[str] = mapped_column(Text, unique=True)
    sort_order: Mapped[int] = mapped_column(Integer, server_default="0")


class Item(Base):
    __tablename__ = "items"
    __table_args__ = (
        CheckConstraint("tracking_mode IN ('individual', 'grouped')", name="tracking_mode_valid"),
        CheckConstraint(
            "(tracking_mode = 'individual' AND quantity = 1) OR "
            "(tracking_mode = 'grouped' AND quantity >= 0)",
            name="quantity_matches_tracking_mode",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    category_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("categories.id", ondelete="RESTRICT"), index=True
    )
    name: Mapped[str] = mapped_column(Text)
    tracking_mode: Mapped[str] = mapped_column(Text)
    quantity: Mapped[int] = mapped_column(Integer)
    condition_id: Mapped[int | None] = mapped_column(
        SmallInteger, ForeignKey("conditions.id", ondelete="RESTRICT"), index=True
    )
    brand: Mapped[str | None] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(Text)
    color: Mapped[str | None] = mapped_column(Text)
    size: Mapped[str | None] = mapped_column(Text)
    material: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    extra_attributes: Mapped[dict[str, Any]] = mapped_column(
        JSONB, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ItemPurpose(Base):
    __tablename__ = "item_purposes"

    item_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("items.id", ondelete="CASCADE"), primary_key=True
    )
    purpose_id: Mapped[int] = mapped_column(
        SmallInteger, ForeignKey("purposes.id", ondelete="RESTRICT"), primary_key=True, index=True
    )


class ItemClimate(Base):
    __tablename__ = "item_climates"

    item_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("items.id", ondelete="CASCADE"), primary_key=True
    )
    climate_id: Mapped[int] = mapped_column(
        SmallInteger, ForeignKey("climates.id", ondelete="RESTRICT"), primary_key=True, index=True
    )


class MeasurementProfile(Base):
    __tablename__ = "measurement_profile"
    __table_args__ = (
        CheckConstraint("id = 1", name="singleton"),
        CheckConstraint("height_cm > 0", name="height_positive"),
        CheckConstraint("weight_kg > 0", name="weight_positive"),
        CheckConstraint("chest_cm > 0", name="chest_positive"),
        CheckConstraint("waist_cm > 0", name="waist_positive"),
        CheckConstraint("hips_cm > 0", name="hips_positive"),
        CheckConstraint("inseam_cm > 0", name="inseam_positive"),
        CheckConstraint("foot_length_cm > 0", name="foot_length_positive"),
    )

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=False)
    height_cm: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    chest_cm: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    waist_cm: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    hips_cm: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    inseam_cm: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    foot_length_cm: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    extra_measurements: Mapped[dict[str, Any]] = mapped_column(
        JSONB, server_default=text("'{}'::jsonb")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class RevisionSession(Base):
    __tablename__ = "revision_sessions"
    __table_args__ = (
        CheckConstraint("status IN ('in_progress', 'completed', 'cancelled')", name="status_valid"),
        CheckConstraint("completed_at >= started_at", name="completion_not_before_start"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    status: Mapped[str] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)


class RevisionCategoryResult(Base):
    __tablename__ = "revision_category_results"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'in_progress', 'completed', 'skipped')", name="status_valid"
        ),
        CheckConstraint("result_state IN ('empty', 'nonempty')", name="result_state_valid"),
        CheckConstraint(
            "status != 'completed' OR (result_state IS NOT NULL AND verified_at IS NOT NULL)",
            name="completed_has_result",
        ),
    )

    revision_session_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("revision_sessions.id", ondelete="CASCADE"), primary_key=True
    )
    category_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("categories.id", ondelete="RESTRICT"), primary_key=True, index=True
    )
    status: Mapped[str] = mapped_column(Text)
    result_state: Mapped[str | None] = mapped_column(Text)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
