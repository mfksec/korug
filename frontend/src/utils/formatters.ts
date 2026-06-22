export const formatDate = (dateString: string | null): string => {
  if (!dateString) return 'Never'
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export const formatConfidenceScore = (score: number): string => {
  return `${Math.round(score)}%`
}

export const getConfidenceColor = (score: number): string => {
  if (score >= 85) return '#d32f2f' // Red
  if (score >= 75) return '#f57c00' // Orange
  return '#fbc02d' // Yellow
}

export const getVulnerabilityTypeLabel = (
  type: 's3_bucket_takeover' | 'cname_orphan' | 'dns_orphan'
): string => {
  const labels: Record<string, string> = {
    s3_bucket_takeover: 'S3 Bucket Takeover',
    cname_orphan: 'CNAME Orphan',
    dns_orphan: 'DNS Orphan',
  }
  return labels[type] || type
}

export const truncateString = (str: string, length: number): string => {
  return str.length > length ? str.substring(0, length) + '...' : str
}

export const sortByDate = (a: string, b: string, descending = true): number => {
  const dateA = new Date(a).getTime()
  const dateB = new Date(b).getTime()
  return descending ? dateB - dateA : dateA - dateB
}
