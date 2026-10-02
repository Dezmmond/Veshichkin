import { describe, expect, it } from 'vitest'
import { findCategoryById, findCategoryPath, parseCategoryId } from './categoryTree'
import { tree } from './fixtures.test-support'

describe('category navigation', () => {
  it('finds a root', () => expect(findCategoryById(tree, 10)).toBe(tree[0]))
  it('finds a nested child', () => expect(findCategoryById(tree, 20)?.name).toBe('Ветка B'))
  it('builds a deep path in root to leaf order', () => {
    expect(findCategoryPath(tree, 30)?.map((entry) => entry.id)).toEqual([10, 20, 30])
  })
  it('builds a root path', () => expect(findCategoryPath(tree, 40)).toEqual([tree[1]]))
  it('returns undefined for unknown IDs', () => {
    expect(findCategoryPath(tree, 999)).toBeUndefined()
    expect(findCategoryById(tree, 999)).toBeUndefined()
  })
  it.each(['0', '-1', '1.5', '1e2', 'abc', '9007199254740992', '', ['10']])(
    'rejects invalid route param %s', (value) => expect(parseCategoryId(value)).toBeUndefined(),
  )
  it('parses a positive integer', () => expect(parseCategoryId('20')).toBe(20))
})
