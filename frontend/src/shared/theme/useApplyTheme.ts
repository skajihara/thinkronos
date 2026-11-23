import { useEffect } from 'react'

import { resolveTheme } from './resolveTheme'
import { useThemeStore } from './themeStore'

const DARK_QUERY = '(prefers-color-scheme: dark)'

/** Keep the `dark` class on <html> in sync with the preference and the OS setting. */
export function useApplyTheme(): void {
  const preference = useThemeStore((state) => state.preference)

  useEffect(() => {
    const media = window.matchMedia(DARK_QUERY)
    const apply = () => {
      const theme = resolveTheme(preference, media.matches)
      document.documentElement.classList.toggle('dark', theme === 'dark')
      document.documentElement.style.colorScheme = theme
    }
    apply()
    media.addEventListener('change', apply)
    return () => {
      media.removeEventListener('change', apply)
    }
  }, [preference])
}
