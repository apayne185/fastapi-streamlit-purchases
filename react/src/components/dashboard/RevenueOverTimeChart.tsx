import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import { CHART_COLORS } from '../../lib/chartTokens'

export interface DailyRevenue {
  date: string
  revenue: number
}

export function RevenueOverTimeChart({
  data,
  currency,
}: {
  data: DailyRevenue[]
  currency: string
}) {
  return (
    <div>
      <h3 className="mb-2 text-sm font-medium text-slate-700">Revenue Over Time ({currency})</h3>
      <ResponsiveContainer width="100%" height={280}>
        <AreaChart data={data} margin={{ top: 8, right: 8, left: 8, bottom: 8 }}>
          <CartesianGrid vertical={false} stroke={CHART_COLORS.gridline} />
          <XAxis
            dataKey="date"
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
          <Area
            type="monotone"
            dataKey="revenue"
            stroke={CHART_COLORS.sequentialBlue}
            strokeWidth={2}
            fill={CHART_COLORS.sequentialBlue}
            fillOpacity={CHART_COLORS.areaFillOpacity}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
