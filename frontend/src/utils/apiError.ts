import { AxiosError } from 'axios'

/** Extract a human-readable message from an API/axios error. */
export const apiErrorMessage = (err: unknown, fallback = 'Something went wrong'): string => {
  const ax = err as AxiosError<{ detail?: unknown }>
  const detail = ax?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail.map((d) => (d && typeof d === 'object' ? (d as { msg?: string }).msg : undefined))
      .filter(Boolean)
      .join(', ')
  }
  return err instanceof Error ? err.message : fallback
}
