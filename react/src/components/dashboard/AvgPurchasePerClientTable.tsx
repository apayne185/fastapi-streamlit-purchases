export function AvgPurchasePerClientTable({ data }: { data: Record<string, number> }) {
  const rows = Object.entries(data).sort((a, b) => b[1] - a[1])

  if (rows.length === 0) {
    return null
  }

  return (
    <div>
      <h3 className="mb-2 text-sm font-medium text-slate-700">Avg Purchase per Client</h3>
      <div className="max-h-72 overflow-y-auto rounded-lg border border-slate-200">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-4 py-2 text-left font-medium text-slate-600">Client</th>
              <th className="px-4 py-2 text-right font-medium text-slate-600">Avg ($)</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white">
            {rows.map(([client, avg]) => (
              <tr key={client}>
                <td className="px-4 py-2 text-slate-900">{client}</td>
                <td className="px-4 py-2 text-right text-slate-700">${avg.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
