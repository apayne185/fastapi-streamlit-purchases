import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import { CHART_COLORS } from '../../lib/chartTokens'

export function SalesForecastChart({
  data,
  forecastDays,
}: {
  data: Record<string, number>
  forecastDays: number
}) {
  const rows = Object.entries(data).map(([day, revenue]) => ({ day, revenue }))

  if (rows.length === 0) {
    return null
  }

  return (
    <div>
      <h3 className="mb-2 text-sm font-medium text-slate-700">
        Sales Forecast — Next {forecastDays} Days
      </h3>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={rows} margin={{ top: 8, right: 8, left: 8, bottom: 8 }}>
          <CartesianGrid vertical={false} stroke={CHART_COLORS.gridline} />
          <XAxis
            dataKey="day"
            tick={{ fontSize: 12, fill: CHART_COLORS.axisText }}
            axisLine={{ stroke: CHART_COLORS.gridline }}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 12, fill: CHART_COLORS.axisText }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            formatter={(value) => [`$${Number(value).toFixed(2)}`, 'Projected revenue']}
          />
          <Line
            type="monotone"
            dataKey="revenue"
            stroke={CHART_COLORS.sequentialBlue}
            strokeWidth={2}
            strokeDasharray="4 3"
            dot={{ r: 4, fill: CHART_COLORS.sequentialBlue }}
          />
        </LineChart>
      </ResponsiveContainer>

      <div className="mt-3 max-h-48 overflow-y-auto rounded-lg border border-slate-200">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-4 py-2 text-left font-medium text-slate-600">Day</th>
              <th className="px-4 py-2 text-right font-medium text-slate-600">
                Projected Revenue ($)
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white">
            {rows.map(({ day, revenue }) => (
              <tr key={day}>
                <td className="px-4 py-2 text-slate-900">{day}</td>
                <td className="px-4 py-2 text-right text-slate-700">${revenue.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
