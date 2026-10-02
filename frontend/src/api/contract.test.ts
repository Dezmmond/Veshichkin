import { describe, expect, expectTypeOf, it } from 'vitest'
import type { components, paths } from './generated/schema'
import openapiJson from '../../openapi.json?raw'
import generatedTypes from './generated/schema.d.ts?raw'
import packageJson from '../../package.json?raw'

describe('generated API contract', () => {
  it('exports health and readiness with their response schemas', () => {
    const schema = JSON.parse(openapiJson)
    for (const path of ['/api/health', '/api/ready']) {
      expect(schema.paths[path].get.responses['200'].content['application/json'].schema).toEqual({
        $ref: '#/components/schemas/HealthResponse',
      })
    }
    expect(schema.paths['/api/ready'].get.responses['503'].content['application/json'].schema).toEqual({
      $ref: '#/components/schemas/ErrorResponse',
    })
    expect(generatedTypes.length).toBeGreaterThan(0)
  })

  it('provides a generation command for exporter and TypeScript generation', () => {
    const manifest = JSON.parse(packageJson)
    expect(manifest.scripts['api:generate']).toContain('scripts/export_openapi.py')
    expect(manifest.scripts['api:generate']).toContain('openapi-typescript openapi.json')
  })

  it('exports Stage 2 paths with their expected methods', () => {
    const schema = JSON.parse(openapiJson)
    const expected = {
      '/api/categories': ['get', 'post'],
      '/api/categories/{category_id}': ['patch', 'delete'],
      '/api/reference/purposes': ['get'],
      '/api/reference/conditions': ['get'],
      '/api/reference/climates': ['get'],
      '/api/items': ['get', 'post'],
      '/api/items/{item_id}': ['get', 'patch', 'delete'],
      '/api/profile/measurements': ['get', 'patch'],
    }
    for (const [path, methods] of Object.entries(expected)) {
      expect(Object.keys(schema.paths[path]).sort()).toEqual([...methods].sort())
    }
  })

  it('exports Item relations, filters, and immutable PATCH fields', () => {
    const schema = JSON.parse(openapiJson)
    for (const name of ['ItemCreate', 'ItemPatch', 'ItemResponse']) {
      const properties = schema.components.schemas[name].properties
      for (const field of ['purpose_ids', 'climate_ids']) {
        expect(properties[field]).toMatchObject({ type: 'array', items: { type: 'integer' } })
      }
    }
    expect(schema.components.schemas.ItemResponse.properties.is_active.type).toBe('boolean')
    const patch = schema.components.schemas.ItemPatch.properties
    expect(patch).not.toHaveProperty('tracking_mode')
    expect(patch).not.toHaveProperty('is_active')
    expect(schema.paths['/api/items'].get.parameters.map((parameter: { name: string }) => parameter.name).sort())
      .toEqual(['category_id', 'climate_id', 'condition_id', 'purpose_id', 'tracking_mode'])
  })

  it('exports nullable profile GET and partial measurement updates', () => {
    const schema = JSON.parse(openapiJson)
    const response = schema.paths['/api/profile/measurements'].get.responses['200'].content['application/json'].schema
    expect(response.anyOf).toEqual(expect.arrayContaining([
      { $ref: '#/components/schemas/MeasurementProfileResponse' },
      { type: 'null' },
    ]))
    const patch = schema.components.schemas.MeasurementProfilePatch
    expect(patch.required ?? []).toEqual([])
    for (const field of ['height_cm', 'weight_kg', 'chest_cm', 'waist_cm', 'hips_cm', 'inseam_cm', 'foot_length_cm']) {
      expect(patch.properties[field].anyOf).toContainEqual({ type: 'null' })
    }
    expect(patch.properties.extra_measurements.type).toBe('object')
    expect(patch.properties.extra_measurements).not.toHaveProperty('anyOf')
  })

  it('allows moving a category to root with a null parent', () => {
    const schema = JSON.parse(openapiJson)
    expect(schema.components.schemas.CategoryPatch.properties.parent_id.anyOf)
      .toContainEqual({ type: 'null' })
  })

  it('provides generated Stage 2 TypeScript types for the typed client', () => {
    type Stage2Paths = '/api/categories' | '/api/categories/{category_id}'
      | '/api/reference/purposes' | '/api/reference/conditions' | '/api/reference/climates'
      | '/api/items' | '/api/items/{item_id}' | '/api/profile/measurements'
    expectTypeOf<Stage2Paths>().toMatchTypeOf<keyof paths>()
    type ProfileGet = paths['/api/profile/measurements']['get']['responses'][200]['content']['application/json']
    expectTypeOf<ProfileGet>().toEqualTypeOf<components['schemas']['MeasurementProfileResponse'] | null>()
    type ItemFilters = NonNullable<paths['/api/items']['get']['parameters']['query']>
    expectTypeOf<keyof ItemFilters>().toEqualTypeOf<'category_id' | 'condition_id' | 'purpose_id' | 'climate_id' | 'tracking_mode'>()
    type ItemPatch = components['schemas']['ItemPatch']
    expectTypeOf<Extract<keyof ItemPatch, 'tracking_mode' | 'is_active'>>().toEqualTypeOf<never>()
  })

})
