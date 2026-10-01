import { describe, expect, it } from 'vitest'
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
})
