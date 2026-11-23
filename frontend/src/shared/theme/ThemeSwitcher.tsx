import { ja } from '@/shared/messages/ja'
import { Button } from '@/shared/ui/button'

import { useThemeStore, type ThemePreference } from './themeStore'

const OPTIONS: readonly ThemePreference[] = ['light', 'dark', 'system']

/** Segmented control for the theme preference (B-07). */
export function ThemeSwitcher() {
  const preference = useThemeStore((state) => state.preference)
  const setPreference = useThemeStore((state) => state.setPreference)

  return (
    <div
      role="group"
      aria-label={ja.theme.label}
      className="inline-flex gap-1 rounded-lg border p-0.5"
    >
      {OPTIONS.map((option) => (
        <Button
          key={option}
          size="sm"
          variant={preference === option ? 'secondary' : 'ghost'}
          aria-pressed={preference === option}
          onClick={() => {
            setPreference(option)
          }}
        >
          {ja.theme[option]}
        </Button>
      ))}
    </div>
  )
}
