import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import { CHART_COLORS } from '../../lib/chartTokens'

export interface CountryRevenue {
  country: string
  revenue: number
}

export function RevenueByCountryChart({
  data,
  currency,
}: {
  data: CountryRevenue[]
  currency: string
}) {
  return (
    <div>
      <h3 className="mb-2 text-sm font-medium text-slate-700">Revenue by Country ({currency})</h3>
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={data} margin={{ top: 8, right: 8, left: 8, bottom: 8 }}>
          <CartesianGrid vertical={false} stroke={CHART_COLORS.gridline} />
          <XAxis
            dataKey="country"
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
            formatter={(value) => [`${currency} ${Number(value).toFixed(2)}`, 'Revenue']}
          />
          <Bar dataKey="revenue" fill={CHART_COLORS.categorical[0]} radius={[4, 4, 0, 0]} maxBarSize={24} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
