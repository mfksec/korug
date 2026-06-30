import { describe, it, expect } from 'vitest'
import { toCsv } from './download'

describe('toCsv', () => {
  it('joins the header and rows with CRLF', () => {
    expect(toCsv(['a', 'b'], [['1', '2'], ['3', '4']])).toBe('a,b\r\n1,2\r\n3,4')
  })

  it('quotes fields containing a comma, quote, or newline (RFC 4180)', () => {
    expect(toCsv(['x'], [['a,b']])).toBe('x\r\n"a,b"')
    expect(toCsv(['x'], [['he said "hi"']])).toBe('x\r\n"he said ""hi"""')
    expect(toCsv(['x'], [['line1\nline2']])).toBe('x\r\n"line1\nline2"')
  })

  it('renders null/undefined as empty and keeps numbers', () => {
    expect(toCsv(['a', 'b', 'c'], [[null, undefined, 42]])).toBe('a,b,c\r\n,,42')
  })

  it('handles a header-only export', () => {
    expect(toCsv(['only'], [])).toBe('only')
  })
})
