import 'react'

declare global {
  interface ImportMeta {
    readonly env: {
      readonly VITE_API_BASE_URL: string
      readonly VITE_APP_NAME: string
    }
  }
}
