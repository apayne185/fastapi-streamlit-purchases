import { useMemo, useState } from 'react'

import { parseApiError } from '../api/client'
import { SUPPORTED_CURRENCIES, type Currency } from '../api/types'
import { AvgPurchasePerClientTable } from '../components/dashboard/AvgPurchasePerClientTable'
import { ClientsPerCountryChart } from '../components/dashboard/ClientsPerCountryChart'
import { KpiTile } from '../components/dashboard/KpiTile'
import { RevenueByCountryChart } from '../components/dashboard/RevenueByCountryChart'
import { RevenueOverTimeChart } from '../components/dashboard/RevenueOverTimeChart'
import { SalesForecastChart } from '../components/dashboard/SalesForecastChart'
import { TopCustomersChart } from '../components/dashboard/TopCustomersChart'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { Select } from '../components/ui/Select'
import { useKpis } from '../hooks/useKpis'
import { usePurchases } from '../hooks/usePurchases'
import { convertAmount } from '../lib/currency'

// KPIs and charts below are computed from the currently fetched page of
// purchases, not the full dataset -- matching Streamlit's dashboard exactly
// (see streamlit/app.py), a known simplification preserved rather than fixed.
const PAGE_SIZE = 500

export function DashboardPage() {
  const [currency, setCurrency] = useState<Currency>('USD')
  const { data, isLoading, isError, error } = usePurchases({ limit: PAGE_SIZE, offset: 0 })

  const [forecastDaysInput, setForecastDaysInput] = useState(5)
  const [kpiForecastDays, setKpiForecastDays] = useState<number | undefined>(undefined)
  const [kpisRequested, setKpisRequested] = useState(false)
  const kpis = useKpis(kpiForecastDays, kpisRequested)

  const summary = useMemo(() => {
    const items = data?.items ?? []
    const displayAmounts = items.map((item) => convertAmount(item.amount, item.currency, currency))

    const totalRevenue = displayAmounts.reduce((sum, amount) => sum + amount, 0)
    const avgOrderValue = items.length > 0 ? totalRevenue / items.length : 0
    const uniqueCustomers = new Set(items.map((item) => item.customer_name)).size

    const revenueByCountryMap = new Map<string, number>()
    const revenueByDateMap = new Map<string, number>()
    const spendByCustomerMap = new Map<string, number>()
    items.forEach((item, i) => {
      const amount = displayAmounts[i]
      revenueByCountryMap.set(item.country, (revenueByCountryMap.get(item.country) ?? 0) + amount)
      revenueByDateMap.set(item.purchase_date, (revenueByDateMap.get(item.purchase_date) ?? 0) + amount)
      spendByCustomerMap.set(item.customer_name, (spendByCustomerMap.get(item.customer_name) ?? 0) + amount)
    })

    const revenueByCountry = [...revenueByCountryMap.entries()]
      .map(([country, revenue]) => ({ country, revenue }))
      .sort((a, b) => b.revenue - a.revenue)

    const revenueOverTime = [...revenueByDateMap.entries()]
      .map(([date, revenue]) => ({ date, revenue }))
      .sort((a, b) => a.date.localeCompare(b.date))

    const topCustomers = [...spendByCustomerMap.entries()]
      .map(([customer, spend]) => ({ customer, spend }))
      .sort((a, b) => b.spend - a.spend)
      .slice(0, 10)
      .sort((a, b) => a.spend - b.spend)

    return {
      itemCount: items.length,
      totalRevenue,
      avgOrderValue,
      uniqueCustomers,
      revenueByCountry,
      revenueOverTime,
      topCustomers,
    }
  }, [data, currency])

  return (
    <div>
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-slate-900">Dashboard</h1>
        <div className="w-32">
          <Select
            label="Currency"
            value={currency}
            onChange={(event) => setCurrency(event.target.value as Currency)}
          >
            {SUPPORTED_CURRENCIES.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </Select>
        </div>
      </div>

      {isError && (
        <p className="mt-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          {parseApiError(error)}
        </p>
      )}

      {isLoading && <p className="mt-8 text-center text-sm text-slate-500">Loading…</p>}

      {!isLoading && summary.itemCount === 0 && !isError && (
        <p className="mt-8 text-center text-sm text-slate-500">No purchases found.</p>
      )}

      {summary.itemCount > 0 && (
        <>
          <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
            <KpiTile label="Total Revenue" value={`${currency} ${summary.totalRevenue.toFixed(2)}`} />
            <KpiTile label="Total Purchases" value={summary.itemCount.toLocaleString()} />
            <KpiTile label="Avg Order Value" value={`${currency} ${summary.avgOrderValue.toFixed(2)}`} />
            <KpiTile label="Unique Customers" value={summary.uniqueCustomers.toLocaleString()} />
          </div>

          <div className="mt-8 grid grid-cols-1 gap-8 lg:grid-cols-2">
            <RevenueByCountryChart data={summary.revenueByCountry} currency={currency} />
            <RevenueOverTimeChart data={summary.revenueOverTime} currency={currency} />
          </div>

          <div className="mt-8">
            <TopCustomersChart data={summary.topCustomers} currency={currency} />
          </div>
        </>
      )}

      <div className="mt-10 border-t border-slate-200 pt-6">
        <h2 className="text-lg font-semibold text-slate-900">KPIs &amp; Sales Forecast</h2>
        <div className="mt-3 flex items-end gap-3">
          <div className="w-40">
            <Input
              label="Forecast horizon (days)"
              type="number"
              min={1}
              max={90}
              value={forecastDaysInput}
              onChange={(event) => setForecastDaysInput(Number(event.target.value))}
            />
          </div>
          <Button
            onClick={() => {
              setKpiForecastDays(forecastDaysInput)
              setKpisRequested(true)
            }}
            disabled={kpis.isFetching}
          >
            {kpis.isFetching ? 'Computing…' : 'Compute KPIs'}
          </Button>
        </div>

        {kpis.isError && (
          <p className="mt-4 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">
            {parseApiError(kpis.error)}
          </p>
        )}

        {kpis.data && (
          <div className="mt-6 grid grid-cols-1 gap-8 lg:grid-cols-2">
            <AvgPurchasePerClientTable data={kpis.data.mean_purchases_per_client} />
            <ClientsPerCountryChart data={kpis.data.clients_per_country} />
            {kpis.data.sales_forecast && (
              <div className="lg:col-span-2">
                <SalesForecastChart data={kpis.data.sales_forecast} forecastDays={forecastDaysInput} />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
