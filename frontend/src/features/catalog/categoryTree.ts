import type { components } from '../../api/generated/schema'

type Category = components['schemas']['CategoryTree']

export function flattenCategories(tree: Category[], depth = 0): { id: number; label: string }[] {
  return tree.flatMap((entry) => [{ id: entry.id, label: `${'↳ '.repeat(depth)}${entry.name}` },
    ...flattenCategories(entry.children ?? [], depth + 1)])
}

export function findCategoryPath(tree: Category[], id: number): Category[] | undefined {
  for (const category of tree) {
    if (category.id === id) return [category]
    const childPath = findCategoryPath(category.children ?? [], id)
    if (childPath) return [category, ...childPath]
  }
  return undefined
}

export function findCategoryById(tree: Category[], id: number): Category | undefined {
  return findCategoryPath(tree, id)?.at(-1)
}

export function parseCategoryId(value: unknown): number | undefined {
  if (typeof value !== 'string' || !/^[0-9]+$/.test(value)) return undefined
  const id = Number(value)
  return Number.isSafeInteger(id) && id > 0 ? id : undefined
}
