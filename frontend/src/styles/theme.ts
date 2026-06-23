import { createTheme, Theme, ThemeProvider } from '@mui/material/styles'
import CssBaseline from '@mui/material/CssBaseline'
import { PaletteMode } from '@mui/material'

const FONT_STACK = [
  'Inter',
  '-apple-system',
  'BlinkMacSystemFont',
  '"Segoe UI"',
  'Roboto',
  '"Helvetica Neue"',
  'Arial',
  'sans-serif',
].join(',')

/**
 * Build the application theme for the given color mode.
 * Light and dark share the same brand hues; surfaces and text invert.
 */
export const createAppTheme = (mode: PaletteMode): Theme => {
  const isDark = mode === 'dark'

  return createTheme({
    palette: {
      mode,
      primary: { main: '#4f46e5', light: '#6366f1', dark: '#4338ca', contrastText: '#fff' },
      secondary: { main: '#0ea5e9', light: '#38bdf8', dark: '#0284c7' },
      success: { main: '#16a34a' },
      warning: { main: '#f59e0b' },
      error: { main: '#dc2626' },
      info: { main: '#0ea5e9' },
      background: {
        default: isDark ? '#0f1117' : '#f6f7fb',
        paper: isDark ? '#171a21' : '#ffffff',
      },
      divider: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(15,23,42,0.08)',
      text: {
        primary: isDark ? '#e6e8ee' : '#1e293b',
        secondary: isDark ? '#9aa4b2' : '#64748b',
      },
    },
    shape: { borderRadius: 12 },
    typography: {
      fontFamily: FONT_STACK,
      h4: { fontWeight: 700, letterSpacing: '-0.02em' },
      h5: { fontWeight: 700, letterSpacing: '-0.01em' },
      h6: { fontWeight: 600 },
      subtitle2: { fontWeight: 600 },
      button: { fontWeight: 600 },
    },
    components: {
      MuiButton: {
        defaultProps: { disableElevation: true },
        styleOverrides: { root: { textTransform: 'none', borderRadius: 10 } },
      },
      MuiPaper: {
        styleOverrides: { root: { backgroundImage: 'none' } },
      },
      MuiCard: {
        styleOverrides: {
          root: {
            borderRadius: 16,
            border: `1px solid ${isDark ? 'rgba(255,255,255,0.06)' : 'rgba(15,23,42,0.06)'}`,
            boxShadow: isDark
              ? '0 1px 2px rgba(0,0,0,0.4)'
              : '0 1px 3px rgba(15,23,42,0.06), 0 1px 2px rgba(15,23,42,0.04)',
          },
        },
      },
      MuiAppBar: {
        defaultProps: { elevation: 0, color: 'default' },
        styleOverrides: {
          root: {
            backgroundColor: isDark ? 'rgba(23,26,33,0.8)' : 'rgba(255,255,255,0.8)',
            backdropFilter: 'blur(8px)',
            borderBottom: `1px solid ${isDark ? 'rgba(255,255,255,0.08)' : 'rgba(15,23,42,0.08)'}`,
          },
        },
      },
      MuiDrawer: {
        styleOverrides: {
          paper: {
            border: 'none',
            backgroundColor: isDark ? '#13151c' : '#ffffff',
            borderRight: `1px solid ${isDark ? 'rgba(255,255,255,0.06)' : 'rgba(15,23,42,0.06)'}`,
          },
        },
      },
      MuiListItemButton: {
        styleOverrides: {
          root: {
            borderRadius: 10,
            marginInline: 8,
            '&.Mui-selected': {
              backgroundColor: isDark ? 'rgba(99,102,241,0.16)' : 'rgba(79,70,229,0.10)',
              '&:hover': { backgroundColor: isDark ? 'rgba(99,102,241,0.24)' : 'rgba(79,70,229,0.16)' },
            },
          },
        },
      },
      MuiTableHead: {
        styleOverrides: {
          root: { '& .MuiTableCell-head': { fontWeight: 700 } },
        },
      },
      MuiChip: { styleOverrides: { root: { fontWeight: 600 } } },
      MuiTextField: { defaultProps: { size: 'small' } },
    },
  })
}

// Backwards-compatible default theme (light).
const theme = createAppTheme('light')

export { theme, ThemeProvider, CssBaseline }
