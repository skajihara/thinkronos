import { ja } from '@/shared/messages/ja'
import { cn } from '@/shared/lib/utils'
import { Button } from '@/shared/ui/button'

import { useHealth } from './useHealth'

/** Shows whether the API and the database respond. */
export function HealthStatus() {
  const { data, isPending, isError, refetch, isFetching } = useHealth()

  let message: string = ja.health.checking
  let tone = 'bg-muted-foreground'
  if (!isPending) {
    if (isError) {
      message = ja.health.unreachable
      tone = 'bg-destructive'
    } else if (data.status === 'ok') {
      message = ja.health.ok
      tone = 'bg-emerald-500'
    } else {
      message = ja.health.degraded
      tone = 'bg-amber-500'
    }
  }

  return (
    <div className="flex items-center gap-3">
      <span aria-hidden className={cn('size-2.5 rounded-full', tone)} />
      <p role="status">{message}</p>
      <Button
        variant="outline"
        size="sm"
        disabled={isFetching}
        onClick={() => {
          void refetch()
        }}
      >
        {ja.health.retry}
      </Button>
    </div>
  )
}
