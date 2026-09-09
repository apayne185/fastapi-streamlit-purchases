import { useQuery } from '@tanstack/react-query'

import { fetchKpis } from '../api/purchases'

export function useKpis(forecastDays: number | undefined, enabled: boolean) {
  return useQuery({
    queryKey: ['kpis', forecastDays],
    queryFn: () => fetchKpis(forecastDays),
    enabled,
  })
}
