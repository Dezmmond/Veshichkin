"""Add the initial editable category taxonomy and reference data.

Revision ID: 0002_reference_data
Revises: 0001_initial_schema
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_reference_data"
down_revision: str | Sequence[str] | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CATEGORY_GROUPS = (
    (
        "Одежда и обувь",
        (
            "Верхняя одежда",
            "Повседневный верх",
            "Повседневный низ",
            "Базовый слой",
            "Бельё и носки",
            "Домашняя одежда",
            "Спортивная одежда",
            "Обувь",
            "Головные уборы",
            "Перчатки и аксессуары",
            "Сумки и переноска",
        ),
    ),
    (
        "Туризм",
        (
            "Рюкзаки",
            "Палатки и укрытие",
            "Спальная система",
            "Приготовление еды",
            "Вода",
            "Освещение",
            "Навигация",
            "Трекинговые палки",
            "Аптечка",
            "Ремонт",
            "Защита вещей от воды",
        ),
    ),
    (
        "Горные лыжи",
        (
            "Одежда и слои",
            "Лыжи",
            "Крепления",
            "Ботинки",
            "Палки",
            "Шлем",
            "Маска",
            "Защита",
            "Чехлы и обслуживание",
        ),
    ),
)

PURPOSES = (
    ("city_work", "Город / работа", 10),
    ("home", "Дом", 20),
    ("boxing", "Бокс", 30),
    ("gym", "Тренажёрный зал", 40),
    ("acrobatics", "Акробатика", 50),
    ("travel", "Путешествия", 60),
    ("hiking", "Пеший поход", 70),
    ("water_trip", "Водный поход", 80),
    ("horse_trip", "Конный поход", 90),
    ("alpine_skiing", "Горные лыжи", 100),
)

CONDITIONS = (
    ("new", "Новое", 0, "Не использовалось или практически не использовалось"),
    ("excellent", "Отличное", 1, "Минимальные следы использования"),
    ("good", "Хорошее", 2, "Обычные следы использования, функциональность сохранена"),
    ("worn", "Изношенное", 3, "Заметный износ, вещь всё ещё пригодна к использованию"),
    (
        "heavily_worn",
        "Сильно изношенное",
        4,
        "Сильный износ, но состояние само по себе не означает решение о замене",
    ),
)

CLIMATES = (
    ("hot", "Жара", 10),
    ("warm", "Тепло", 20),
    ("cool", "Прохладно", 30),
    ("cold", "Холод", 40),
    ("severe_cold", "Сильный холод", 50),
    ("wet", "Сырая / дождливая погода", 60),
)

# Local SQL definitions keep this historical migration independent of runtime models.
categories = sa.table(
    "categories",
    sa.column("id", sa.BigInteger),
    sa.column("name", sa.Text),
    sa.column("parent_id", sa.BigInteger),
    sa.column("sort_order", sa.Integer),
)
purposes = sa.table(
    "purposes",
    sa.column("code", sa.Text),
    sa.column("name", sa.Text),
    sa.column("sort_order", sa.Integer),
)
conditions = sa.table(
    "conditions",
    sa.column("code", sa.Text),
    sa.column("name", sa.Text),
    sa.column("rank", sa.Integer),
    sa.column("description", sa.Text),
)
climates = sa.table(
    "climates",
    sa.column("code", sa.Text),
    sa.column("name", sa.Text),
    sa.column("sort_order", sa.Integer),
)


def upgrade() -> None:
    for root_order, (root_name, child_names) in enumerate(CATEGORY_GROUPS, start=1):
        # RETURNING stays in SQL: no generated identity values are read by Python.
        root = (
            sa.insert(categories)
            .values(name=root_name, sort_order=root_order * 10)
            .returning(categories.c.id)
            .cte("new_root")
        )
        children = sa.values(
            sa.column("name", sa.Text),
            sa.column("sort_order", sa.Integer),
            name="seed_children",
        ).data([(name, order * 10) for order, name in enumerate(child_names, start=1)])
        op.execute(
            sa.insert(categories).from_select(
                ["name", "parent_id", "sort_order"],
                sa.select(children.c.name, root.c.id, children.c.sort_order).select_from(
                    children.join(root, sa.true())
                ),
            )
        )

    op.bulk_insert(
        purposes,
        [{"code": code, "name": name, "sort_order": order} for code, name, order in PURPOSES],
    )
    op.bulk_insert(
        conditions,
        [
            {"code": code, "name": name, "rank": rank, "description": description}
            for code, name, rank, description in CONDITIONS
        ],
    )
    op.bulk_insert(
        climates,
        [{"code": code, "name": name, "sort_order": order} for code, name, order in CLIMATES],
    )


def downgrade() -> None:
    for root_name, child_names in CATEGORY_GROUPS:
        root_ids = sa.select(categories.c.id).where(
            categories.c.name == root_name, categories.c.parent_id.is_(None)
        )
        op.execute(
            sa.delete(categories).where(
                categories.c.parent_id.in_(root_ids), categories.c.name.in_(child_names)
            )
        )
    op.execute(
        sa.delete(categories).where(
            categories.c.parent_id.is_(None),
            categories.c.name.in_([root_name for root_name, _ in CATEGORY_GROUPS]),
        )
    )
    op.execute(sa.delete(purposes).where(purposes.c.code.in_([row[0] for row in PURPOSES])))
    op.execute(sa.delete(conditions).where(conditions.c.code.in_([row[0] for row in CONDITIONS])))
    op.execute(sa.delete(climates).where(climates.c.code.in_([row[0] for row in CLIMATES])))
