import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import { CHART_COLORS } from '../../lib/chartTokens'

export function ClientsPerCountryChart({ data }: { data: Record<string, number> }) {
  const rows = Object.entries(data)
    .map(([country, clients]) => ({ country, clients }))
    .sort((a, b) => b.clients - a.clients)

  if (rows.length === 0) {
    return null
  }

  return (
    <div>
      <h3 className="mb-2 text-sm font-medium text-slate-700">Clients per Country</h3>
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={rows} margin={{ top: 8, right: 8, left: 8, bottom: 8 }}>
          <CartesianGrid vertical={false} stroke={CHART_COLORS.gridline} />
          <XAxis
            dataKey="country"
            tick={{ fontSize: 12, fill: CHART_COLORS.axisText }}
            axisLine={{ stroke: CHART_COLORS.gridline }}
            tickLine={false}
          />
          <YAxis
            allowDecimals={false}
            tick={{ fontSize: 12, fill: CHART_COLORS.axisText }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip formatter={(value) => [String(value), 'Clients']} />
          <Bar dataKey="clients" fill={CHART_COLORS.sequentialBlue} radius={[4, 4, 0, 0]} maxBarSize={24} />
        </BarChart>
      </ResponsiveContainer>

      <div className="mt-3 max-h-48 overflow-y-auto rounded-lg border border-slate-200">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-4 py-2 text-left font-medium text-slate-600">Country</th>
              <th className="px-4 py-2 text-right font-medium text-slate-600">Clients</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white">
            {rows.map(({ country, clients }) => (
              <tr key={country}>
                <td className="px-4 py-2 text-slate-900">{country}</td>
                <td className="px-4 py-2 text-right text-slate-700">{clients}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
