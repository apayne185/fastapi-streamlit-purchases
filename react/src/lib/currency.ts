// Illustrative static rates, ported 1:1 from streamlit/app.py's RATES_TO_USD
// -- not live/real-time, matching the existing dashboard's known simplification.
export const RATES_TO_USD: Record<string, number> = {
  USD: 1.0,
  EUR: 1.08,
  GBP: 1.27,
  JPY: 0.0067,
  CAD: 0.74,
  AUD: 0.65,
  CHF: 1.13,
  SEK: 0.095,
  NOK: 0.094,
  DKK: 0.145,
}

export function toUsd(amount: number, currency: string): number {
  return amount * (RATES_TO_USD[currency] ?? 1.0)
}

export function convert(amountUsd: number, target: string): number {
  return amountUsd / (RATES_TO_USD[target] ?? 1.0)
}

export function convertAmount(amount: number, from: string, to: string): number {
  return convert(toUsd(amount, from), to)
}
