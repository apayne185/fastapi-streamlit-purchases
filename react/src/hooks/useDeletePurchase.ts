import { useMutation, useQueryClient } from '@tanstack/react-query'

import { deletePurchase } from '../api/purchases'

export function useDeletePurchase() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deletePurchase,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['purchases'] })
    },
  })
}
