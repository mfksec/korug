import React, { createContext, useContext, useMemo, useState, useCallback } from 'react'
import { PaletteMode } from '@mui/material'
import { ThemeProvider, CssBaseline } from '@mui/material'
import { createAppTheme } from '@/styles/theme'

interface ColorModeContextValue {
  mode: PaletteMode
  toggle: () => void
  setMode: (mode: PaletteMode) => void
}

const ColorModeContext = createContext<ColorModeContextValue>({
  mode: 'light',
  toggle: () => {},
  setMode: () => {},
})

const STORAGE_KEY = 'korug-color-mode'

const getInitialMode = (): PaletteMode => {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored === 'light' || stored === 'dark') return stored
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

export const ColorModeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [mode, setMode] = useState<PaletteMode>(getInitialMode)

  const setModeExplicit = useCallback((next: PaletteMode) => {
    localStorage.setItem(STORAGE_KEY, next)
    setMode(next)
  }, [])

  const toggle = useCallback(() => {
    setMode((prev) => {
      const next = prev === 'light' ? 'dark' : 'light'
      localStorage.setItem(STORAGE_KEY, next)
      return next
    })
  }, [])

  const theme = useMemo(() => createAppTheme(mode), [mode])
  const value = useMemo(() => ({ mode, toggle, setMode: setModeExplicit }), [mode, toggle, setModeExplicit])

  return (
    <ColorModeContext.Provider value={value}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        {children}
      </ThemeProvider>
    </ColorModeContext.Provider>
  )
}

export const useColorMode = () => useContext(ColorModeContext)
