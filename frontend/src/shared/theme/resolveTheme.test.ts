import { describe, expect, it } from 'vitest'

import { resolveTheme } from './resolveTheme'

describe('resolveTheme', () => {
  it('follows the OS setting when the preference is system', () => {
    expect(resolveTheme('system', true)).toBe('dark')
    expect(resolveTheme('system', false)).toBe('light')
  })

  it('uses the explicit preference regardless of the OS setting', () => {
    expect(resolveTheme('light', true)).toBe('light')
    expect(resolveTheme('dark', false)).toBe('dark')
  })
})
