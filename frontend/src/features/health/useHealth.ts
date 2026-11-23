import { useQuery } from '@tanstack/react-query'

import { apiClient } from '@/shared/api/client'
import type { components } from '@/shared/api/schema'

export type Health = components['schemas']['HealthResponse']

/** Ask the API whether it and the database are reachable. 503 still carries a body. */
export function useHealth() {
  return useQuery({
    queryKey: ['healthz'],
    queryFn: async (): Promise<Health> => {
      const { data, error } = await apiClient.GET('/healthz')
      // The 503 response has the same shape, so both branches are a Health.
      return data ?? error
    },
    retry: false,
  })
}
