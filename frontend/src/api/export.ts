import client from './client'

// Export endpoints. Requests are authenticated (Bearer token via the shared
// client), so downloads must go through axios as a Blob rather than a bare
// <a href> — a plain link wouldn't carry the Authorization header.
export const exportAPI = {
  /** Fetch the XLSX export for a domain as a Blob. */
  domainXlsx: async (domainId: number): Promise<Blob> => {
    const response = await client.get(`/api/export/xlsx/${domainId}`, {
      responseType: 'blob',
    })
    return response.data as Blob
  },
}
