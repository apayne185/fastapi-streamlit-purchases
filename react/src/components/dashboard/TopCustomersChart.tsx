import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import { CHART_COLORS } from '../../lib/chartTokens'

export interface CustomerSpend {
  customer: string
  spend: number
}

export function TopCustomersChart({
  data,
  currency,
}: {
  data: CustomerSpend[]
  currency: string
}) {
  return (
    <div>
      <h3 className="mb-2 text-sm font-medium text-slate-700">Top 10 Customers ({currency})</h3>
      <ResponsiveContainer width="100%" height={320}>
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 8, right: 16, left: 8, bottom: 8 }}
        >
          <CartesianGrid horizontal={false} stroke={CHART_COLORS.gridline} />
          <XAxis
            type="number"
            tick={{ fontSize: 12, fill: CHART_COLORS.axisText }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            dataKey="customer"
            type="category"
            width={110}
            tick={{ fontSize: 12, fill: CHART_COLORS.axisText }}
            axisLine={{ stroke: CHART_COLORS.gridline }}
            tickLine={false}
          />
          <Tooltip
            formatter={(value) => [`${currency} ${Number(value).toFixed(2)}`, 'Total spend']}
          />
          <Bar dataKey="spend" fill={CHART_COLORS.sequentialBlue} radius={[0, 4, 4, 0]} maxBarSize={20} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
