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
 * Brand palette — turquoise + deep petrol, the single source of truth for
 * brand colour. Adjust a value here and it propagates across the whole UI.
 */
export const BRAND = {
  turquoise: '#0BA5A5',      // primary
  turquoiseLight: '#3FC0C0',
  turquoiseDark: '#078A8A',
  petrol: '#0E2F33',         // dark sidebar / accent surface (used in both modes)
  petrolDark: '#0A2125',
  ink: '#14252A',            // near-black text with a teal undertone
  // semantic (severity) colours
  success: '#16A34A',
  warning: '#F4B740',
  error: '#E5484D',
  info: '#0EA5E9',
} as const

/** Sidebar surface colour for the current mode (deep petrol, dark in both). */
export const sidebarBg = (isDark: boolean): string => (isDark ? BRAND.petrolDark : BRAND.petrol)

/**
 * Build the application theme for the given color mode.
 * Light and dark share the same brand hues; surfaces and text invert.
 */
export const createAppTheme = (mode: PaletteMode): Theme => {
  const isDark = mode === 'dark'

  return createTheme({
    palette: {
      mode,
      primary: { main: BRAND.turquoise, light: BRAND.turquoiseLight, dark: BRAND.turquoiseDark, contrastText: '#fff' },
      secondary: { main: BRAND.petrol, light: '#1F4A50', dark: BRAND.petrolDark, contrastText: '#fff' },
      success: { main: BRAND.success },
      warning: { main: BRAND.warning },
      error: { main: BRAND.error },
      info: { main: BRAND.info },
      background: {
        default: isDark ? '#0B1416' : '#F4F7F8',
        paper: isDark ? '#12201F' : '#ffffff',
      },
      divider: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(14,47,51,0.10)',
      text: {
        primary: isDark ? '#E6EEF0' : BRAND.ink,
        secondary: isDark ? '#8FA3A6' : '#5A6B70',
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
            // Deep petrol sidebar in both modes — the brand's signature surface.
            backgroundColor: sidebarBg(isDark),
            color: 'rgba(255,255,255,0.82)',
            borderRight: 'none',
          },
        },
      },
      MuiListItemButton: {
        styleOverrides: {
          root: {
            borderRadius: 10,
            marginInline: 8,
            color: 'rgba(255,255,255,0.78)',
            '& .MuiListItemIcon-root': { color: 'rgba(255,255,255,0.6)' },
            '&:hover': { backgroundColor: 'rgba(255,255,255,0.06)' },
            '&.Mui-selected': {
              backgroundColor: 'rgba(11,165,165,0.22)',
              color: '#fff',
              '& .MuiListItemIcon-root': { color: BRAND.turquoiseLight },
              '&:hover': { backgroundColor: 'rgba(11,165,165,0.30)' },
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
