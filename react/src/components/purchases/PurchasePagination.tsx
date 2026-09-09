import { Button } from '../ui/Button'

const PAGE_SIZE_OPTIONS = [100, 250, 500, 1000]

interface PurchasePaginationProps {
  offset: number
  limit: number
  total: number
  onOffsetChange: (offset: number) => void
  onLimitChange: (limit: number) => void
}

export function PurchasePagination({
  offset,
  limit,
  total,
  onOffsetChange,
  onLimitChange,
}: PurchasePaginationProps) {
  const start = total === 0 ? 0 : offset + 1
  const end = Math.min(offset + limit, total)

  return (
    <div className="flex items-center justify-between py-3">
      <div className="flex items-center gap-2 text-sm text-slate-600">
        <span>
          {start}–{end} of {total}
        </span>
        <label className="ml-4 flex items-center gap-2">
          Page size
          <select
            className="rounded-md border border-slate-300 px-2 py-1 text-sm"
            value={limit}
            onChange={(event) => onLimitChange(Number(event.target.value))}
          >
            {PAGE_SIZE_OPTIONS.map((size) => (
              <option key={size} value={size}>
                {size}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="flex gap-2">
        <Button
          variant="secondary"
          disabled={offset === 0}
          onClick={() => onOffsetChange(Math.max(0, offset - limit))}
        >
          Previous
        </Button>
        <Button
          variant="secondary"
          disabled={offset + limit >= total}
          onClick={() => onOffsetChange(offset + limit)}
        >
          Next
        </Button>
      </div>
    </div>
  )
}
