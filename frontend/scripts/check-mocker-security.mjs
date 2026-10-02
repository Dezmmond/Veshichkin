import assert from 'node:assert/strict'
import { mkdtemp, mkdir, writeFile, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { resolveConfig } from 'vite'
import { interceptorPlugin } from '@vitest/mocker/node'

// Exercise the advisory's WebSocket registration path with disposable marker files.
// No listener is opened and no real secrets are read.
const directory = await mkdtemp(join(tmpdir(), 'veshichkin-mocker-security-'))
try {
  const root = join(directory, 'project')
  await mkdir(root)
  await writeFile(join(directory, 'outside.js'), 'outside marker')
  await writeFile(join(root, '.env'), 'denied marker')
  await writeFile(join(root, 'allowed.js'), 'export const marker = true')
  const config = await resolveConfig({
    configFile: false,
    root,
    server: { fs: { strict: true, allow: [root], deny: ['.env'] } },
  }, 'serve')
  const handlers = new Map()
  const plugin = interceptorPlugin()
  plugin.configureServer({
    config,
    ws: { on: (name, handler) => handlers.set(name, handler), send: () => {} },
  })
  const register = handlers.get('vitest:interceptor:register')
  assert.equal(typeof register, 'function')
  for (const [id, redirect, expected] of [
    ['outside', 'mock:../outside.js', undefined],
    ['denied', 'file:///.env', undefined],
    ['allowed', 'file:///allowed.js', 'export const marker = true'],
  ]) {
    register({ type: 'redirect', raw: id, id, url: `/${id}`, redirect })
    assert.equal(await plugin.load.handler(id), expected, id)
    console.log(`PASS: ${id}`)
  }
} finally {
  await rm(directory, { recursive: true, force: true })
}
