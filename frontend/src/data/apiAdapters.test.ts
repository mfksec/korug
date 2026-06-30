import { describe, it, expect } from 'vitest'
import { timeAgo } from './apiAdapters'

const ago = (ms: number) => new Date(Date.now() - ms).toISOString()

describe('timeAgo', () => {
  it('returns "never" for empty or unparseable input', () => {
    expect(timeAgo(null)).toBe('never')
    expect(timeAgo(undefined)).toBe('never')
    expect(timeAgo('not-a-date')).toBe('never')
  })

  it('formats recent timestamps in compact units', () => {
    expect(timeAgo(ago(10_000))).toBe('just now')
    expect(timeAgo(ago(5 * 60_000))).toBe('5 min ago')
    expect(timeAgo(ago(3 * 3_600_000))).toBe('3 h ago')
    expect(timeAgo(ago(2 * 86_400_000))).toBe('2 d ago')
  })

  it('treats a naive (no-timezone) timestamp as UTC', () => {
    // Strip the trailing Z + fractional seconds to simulate the API's naive UTC.
    const naive = ago(5 * 60_000).replace(/\.\d+Z$/, '')
    expect(timeAgo(naive)).toBe('5 min ago')
  })
})
