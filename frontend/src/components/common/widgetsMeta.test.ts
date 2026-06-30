import { describe, it, expect } from 'vitest'
import { vulnTypeMeta, changeTypeMeta, riskMeta, severityMeta, confidenceColor } from './Widgets'

describe('vulnTypeMeta', () => {
  it('maps known takeover types', () => {
    expect(vulnTypeMeta('subdomain_takeover').label).toBe('Subdomain takeover')
    expect(vulnTypeMeta('s3_bucket_takeover').color).toBe('error')
  })

  it('derives CVE and nuclei labels from the prefix', () => {
    expect(vulnTypeMeta('cve:CVE-2021-44228').label).toBe('CVE-2021-44228')
    expect(vulnTypeMeta('nuclei:exposed-panel').label).toBe('exposed-panel')
  })

  it('falls back to a humanized label for unknown types', () => {
    expect(vulnTypeMeta('weird_thing').label).toBe('weird thing')
  })
})

describe('changeTypeMeta', () => {
  it('labels known change types', () => {
    expect(changeTypeMeta('subdomain_added').label).toBe('New subdomain')
    expect(changeTypeMeta('new_certificate').color).toBe('secondary')
  })

  it('humanizes unknown change types', () => {
    expect(changeTypeMeta('some_new_event').label).toBe('some new event')
  })
})

describe('risk / confidence / severity meta', () => {
  it('riskMeta maps levels to chip colors', () => {
    expect(riskMeta('high').color).toBe('error')
    expect(riskMeta('none').color).toBe('default')
  })

  it('confidenceColor applies the right thresholds', () => {
    expect(confidenceColor(95)).toBe('error')
    expect(confidenceColor(85)).toBe('warning')
    expect(confidenceColor(50)).toBe('info')
  })

  it('severityMeta maps alert severities', () => {
    expect(severityMeta('high').label).toBe('Critical')
    expect(severityMeta('info').color).toBe('secondary')
  })
})
