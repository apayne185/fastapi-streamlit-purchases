import { describe, expect, it } from 'vitest'

import { convert, convertAmount, toUsd } from './currency'

describe('toUsd', () => {
  it('passes USD through unchanged', () => {
    expect(toUsd(100, 'USD')).toBe(100)
  })

  it('converts using the fixed rate table', () => {
    expect(toUsd(100, 'EUR')).toBeCloseTo(108, 5)
  })

  it('falls back to a 1.0 rate for an unknown currency', () => {
    expect(toUsd(100, 'XYZ')).toBe(100)
  })
})

describe('convert', () => {
  it('converts USD amounts into the target currency', () => {
    expect(convert(108, 'EUR')).toBeCloseTo(100, 5)
  })
})

describe('convertAmount', () => {
  it('round-trips an amount through the same currency unchanged', () => {
    expect(convertAmount(42.5, 'GBP', 'GBP')).toBeCloseTo(42.5, 5)
  })

  it('converts between two non-USD currencies via USD', () => {
    // 100 EUR -> 108 USD -> 108/1.27 GBP
    expect(convertAmount(100, 'EUR', 'GBP')).toBeCloseTo(108 / 1.27, 5)
  })
})
