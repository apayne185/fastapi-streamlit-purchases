import { Input } from '../ui/Input'

export interface PurchaseFilterValues {
  country: string
  startDate: string
  endDate: string
}

interface PurchaseFiltersProps {
  values: PurchaseFilterValues
  onChange: (values: PurchaseFilterValues) => void
}

export function PurchaseFilters({ values, onChange }: PurchaseFiltersProps) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
      <Input
        label="Country"
        name="country"
        placeholder="e.g. Tunisia"
        value={values.country}
        onChange={(event) => onChange({ ...values, country: event.target.value })}
      />
      <Input
        label="From"
        name="startDate"
        type="date"
        value={values.startDate}
        onChange={(event) => onChange({ ...values, startDate: event.target.value })}
      />
      <Input
        label="To"
        name="endDate"
        type="date"
        value={values.endDate}
        onChange={(event) => onChange({ ...values, endDate: event.target.value })}
      />
    </div>
  )
}
