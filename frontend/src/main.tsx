import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import { ColorModeProvider } from '@/contexts/ColorModeContext'
import { AuthProvider } from '@/contexts/AuthContext'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ColorModeProvider>
      <AuthProvider>
        <App />
      </AuthProvider>
    </ColorModeProvider>
  </React.StrictMode>,
)
