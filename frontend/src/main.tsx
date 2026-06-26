import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import { AuthProvider } from '@/contexts/AuthContext'
import './index.css'

// App calls useAuth() at the top of its body, so AuthProvider must wrap it.
// Color-mode/theme providers live inside App (ThemeModeProvider).
ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <AuthProvider>
      <App />
    </AuthProvider>
  </React.StrictMode>
)
