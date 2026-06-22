import { useState, useCallback } from 'react'
import { domainAPI } from '@/api/domains'
import { Domain } from '@/types'

export const useDomains = () => {
  const [domains, setDomains] = useState<Domain[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchDomains = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const data = await domainAPI.list()
      setDomains(data)
    } catch (err: any) {
      const message = err.response?.data?.detail || 'Failed to fetch domains'
      setError(message)
    } finally {
      setIsLoading(false)
    }
  }, [])

  const addDomain = useCallback(async (domain_name: string) => {
    setError(null)
    try {
      const newDomain = await domainAPI.create(domain_name)
      setDomains((prev) => [...prev, newDomain])
      return newDomain
    } catch (err: any) {
      const message = err.response?.data?.detail || 'Failed to add domain'
      setError(message)
      throw err
    }
  }, [])

  const deleteDomain = useCallback(async (id: number) => {
    setError(null)
    try {
      await domainAPI.delete(id)
      setDomains((prev) => prev.filter((d) => d.id !== id))
    } catch (err: any) {
      const message = err.response?.data?.detail || 'Failed to delete domain'
      setError(message)
      throw err
    }
  }, [])

  const updateDomain = useCallback(async (id: number, data: Partial<Domain>) => {
    setError(null)
    try {
      const updated = await domainAPI.update(id, data)
      setDomains((prev) =>
        prev.map((d) => (d.id === id ? updated : d))
      )
      return updated
    } catch (err: any) {
      const message = err.response?.data?.detail || 'Failed to update domain'
      setError(message)
      throw err
    }
  }, [])

  return {
    domains,
    isLoading,
    error,
    fetchDomains,
    addDomain,
    deleteDomain,
    updateDomain,
  }
}
