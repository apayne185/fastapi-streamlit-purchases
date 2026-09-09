import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { z } from 'zod'

import { parseApiError } from '../../api/client'
import { SUPPORTED_CURRENCIES } from '../../api/types'
import { useCreatePurchase } from '../../hooks/useCreatePurchase'
import { Button } from '../ui/Button'
import { Input } from '../ui/Input'
import { Select } from '../ui/Select'

const purchaseSchema = z.object({
  customer_name: z.string().min(1, 'Customer name is required'),
  country: z.string().min(1, 'Country is required'),
  purchase_date: z.string().min(1, 'Date is required'),
  amount: z.coerce.number().gt(0, 'Amount must be greater than 0'),
  currency: z.enum(SUPPORTED_CURRENCIES),
})

type PurchaseFormInput = z.input<typeof purchaseSchema>
type PurchaseFormOutput = z.output<typeof purchaseSchema>

export function PurchaseForm({ onCreated }: { onCreated?: () => void }) {
  const createPurchase = useCreatePurchase()

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<PurchaseFormInput, unknown, PurchaseFormOutput>({
    resolver: zodResolver(purchaseSchema),
    defaultValues: { currency: 'USD', customer_name: '', country: '', purchase_date: '', amount: 0 },
  })

  const onSubmit = async (values: PurchaseFormOutput) => {
    try {
      await createPurchase.mutateAsync(values)
    } catch {
      // Surfaced via createPurchase.isError/error below; nothing further to do here.
      return
    }
    reset({ customer_name: '', country: '', purchase_date: '', amount: 0, currency: 'USD' })
    onCreated?.()
  }

  return (
    <form className="flex max-w-md flex-col gap-4" onSubmit={handleSubmit(onSubmit)}>
      <Input
        label="Customer name"
        error={errors.customer_name?.message}
        {...register('customer_name')}
      />
      <Input label="Country" error={errors.country?.message} {...register('country')} />
      <Input
        label="Purchase date"
        type="date"
        error={errors.purchase_date?.message}
        {...register('purchase_date')}
      />
      <Input
        label="Amount"
        type="number"
        step="0.01"
        error={errors.amount?.message}
        {...register('amount')}
      />
      <Select label="Currency" error={errors.currency?.message} {...register('currency')}>
        {SUPPORTED_CURRENCIES.map((currency) => (
          <option key={currency} value={currency}>
            {currency}
          </option>
        ))}
      </Select>

      {createPurchase.isError && (
        <p className="text-sm text-red-600">{parseApiError(createPurchase.error)}</p>
      )}
      {createPurchase.isSuccess && (
        <p className="text-sm text-emerald-600">Purchase added.</p>
      )}

      <Button type="submit" disabled={isSubmitting}>
        {isSubmitting ? 'Saving…' : 'Add purchase'}
      </Button>
    </form>
  )
}
