import { useMutation, useQueryClient } from '@tanstack/react-query'

import { bulkUploadPurchases } from '../api/purchases'

export function useBulkUpload() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: bulkUploadPurchases,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['purchases'] })
    },
  })
}
