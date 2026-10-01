from collections.abc import Mapping, Sequence

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from veshichkin.categories.schemas import CategoryCreate, CategoryPatch, CategoryTree
from veshichkin.core.errors import ApplicationError
from veshichkin.db.models import Category, Item, RevisionCategoryResult


def validate_parent(
    category_id: int | None, parent_id: int | None, parents: Mapping[int, int | None]
) -> None:
    if parent_id is None:
        return
    if parent_id == category_id:
        raise ApplicationError("category_cycle", "Category hierarchy would contain a cycle", 409)
    if parent_id not in parents:
        raise ApplicationError("category_parent_not_found", "Parent category not found", 404)
    visited: set[int] = set()
    current: int | None = parent_id
    while current is not None:
        if current == category_id or current in visited:
            raise ApplicationError(
                "category_cycle", "Category hierarchy would contain a cycle", 409
            )
        visited.add(current)
        current = parents[current]


def build_tree(categories: Sequence[Category]) -> list[CategoryTree]:
    ordered = sorted(
        categories, key=lambda category: (category.sort_order, category.name, category.id)
    )
    nodes = {category.id: CategoryTree.model_validate(category) for category in ordered}
    roots: list[CategoryTree] = []
    for category in ordered:
        node = nodes[category.id]
        if category.parent_id is None:
            roots.append(node)
        else:
            nodes[category.parent_id].children.append(node)
    return roots


def list_categories(session: Session) -> list[CategoryTree]:
    return build_tree(session.scalars(select(Category)).all())


def get_category(session: Session, category_id: int) -> Category:
    category = session.get(Category, category_id)
    if category is None:
        raise ApplicationError("category_not_found", "Category not found", 404)
    return category


def check_parent(session: Session, category_id: int | None, parent_id: int | None) -> None:
    parents = {category.id: category.parent_id for category in session.scalars(select(Category))}
    validate_parent(category_id, parent_id, parents)


def create_category(session: Session, payload: CategoryCreate) -> Category:
    check_parent(session, None, payload.parent_id)
    category = Category(**payload.model_dump())
    session.add(category)
    session.flush()
    return category


def patch_category(session: Session, category_id: int, payload: CategoryPatch) -> Category:
    if "parent_id" in payload.model_fields_set:
        # Serialize reparenting so concurrent valid moves cannot jointly create a cycle.
        session.execute(text("LOCK TABLE categories IN SHARE ROW EXCLUSIVE MODE"))
    category = get_category(session, category_id)
    if "parent_id" in payload.model_fields_set:
        check_parent(session, category_id, payload.parent_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(category, field, value)
    session.flush()
    return category


def delete_category(session: Session, category_id: int) -> None:
    category = get_category(session, category_id)
    dependencies = (
        select(Category.id).where(Category.parent_id == category_id),
        select(Item.id).where(Item.category_id == category_id),
        select(RevisionCategoryResult.category_id).where(
            RevisionCategoryResult.category_id == category_id
        ),
    )
    if any(session.scalar(query.limit(1)) is not None for query in dependencies):
        raise ApplicationError("category_in_use", "Category is in use", 409)
    session.delete(category)
    session.flush()
