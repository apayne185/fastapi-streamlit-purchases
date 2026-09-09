import { useState } from 'react'

import { parseApiError } from '../../api/client'
import { useDeletePurchase } from '../../hooks/useDeletePurchase'
import { Button } from '../ui/Button'
import { ConfirmDialog } from '../ui/ConfirmDialog'

export function DeletePurchaseButton({ purchaseId }: { purchaseId: number }) {
  const [confirming, setConfirming] = useState(false)
  const deletePurchase = useDeletePurchase()

  return (
    <>
      <Button variant="danger" onClick={() => setConfirming(true)}>
        Delete
      </Button>
      <ConfirmDialog
        open={confirming}
        title="Delete purchase"
        description={`Delete purchase #${purchaseId}? This cannot be undone.`}
        confirmLabel="Delete"
        isConfirming={deletePurchase.isPending}
        onCancel={() => setConfirming(false)}
        onConfirm={() => {
          deletePurchase.mutate(purchaseId, {
            onSuccess: () => setConfirming(false),
          })
        }}
      />
      {deletePurchase.isError && (
        <p className="mt-1 text-xs text-red-600">{parseApiError(deletePurchase.error)}</p>
      )}
    </>
  )
}
