import { HealthStatus } from '@/features/health/HealthStatus'
import { ja } from '@/shared/messages/ja'
import { ThemeSwitcher } from '@/shared/theme/ThemeSwitcher'
import { useApplyTheme } from '@/shared/theme/useApplyTheme'

export function App() {
  useApplyTheme()

  return (
    <div className="min-h-svh">
      <header className="flex items-center justify-between border-b px-6 py-3">
        <h1 className="text-lg font-semibold">{ja.appName}</h1>
        <ThemeSwitcher />
      </header>
      <main className="p-6">
        <HealthStatus />
      </main>
    </div>
  )
}
