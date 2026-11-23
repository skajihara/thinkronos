import type { ThemePreference } from './themeStore'

/** Resolve the preference to the theme actually shown. */
export function resolveTheme(preference: ThemePreference, prefersDark: boolean): 'light' | 'dark' {
  if (preference === 'system') return prefersDark ? 'dark' : 'light'
  return preference
}
