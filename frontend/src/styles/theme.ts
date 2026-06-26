import { createContext, useContext } from 'react'
import { createTheme, Theme, alpha } from '@mui/material/styles'

/**
 * Körüg theme — a clean, security-tool design language with a darker feel.
 * Supports light & dark modes. The left navigation rail stays dark in both
 * modes (a deep teal in light, near-black slate in dark) as a brand signature.
 */

export type AppMode = 'light' | 'dark'

// ---- Custom palette extensions (module augmentation) ----
declare module '@mui/material/styles' {
  interface Palette {
    brand: { main: string; text: string; subtle: string }
    sidebar: { bg: string; bg2: string; text: string; textActive: string; activeBg: string; border: string }
    surface: { subtle: string; raised: string }
  }
  interface PaletteOptions {
    brand?: { main: string; text: string; subtle: string }
    sidebar?: { bg: string; bg2: string; text: string; textActive: string; activeBg: string; border: string }
    surface?: { subtle: string; raised: string }
  }
}

const FONT_BODY = '"Lato", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
const FONT_DISPLAY = '"Manrope", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
export const FONT_MONO = '"Roboto Mono", ui-monospace, SFMono-Regular, Menlo, Consolas, monospace'

const light = {
  bg: 'rgb(245,247,249)',
  paper: '#ffffff',
  surfaceSubtle: 'rgb(238,242,245)',
  surfaceRaised: 'rgb(245,247,249)',
  border: 'rgb(224,230,235)',
  textPrimary: 'rgb(26,28,28)',
  textSecondary: 'rgb(64,81,94)',
  textTertiary: 'rgb(96,117,133)',
  brand: 'rgb(10,166,184)',
  brandText: 'rgb(6,124,137)',
  brandSubtle: 'rgb(231,246,248)',
  green: 'rgb(15,169,128)',
  greenDark: 'rgb(11,131,99)',
  blue: 'rgb(31,108,224)',
  orange: 'rgb(223,148,17)',
  red: 'rgb(237,85,84)',
  purple: 'rgb(114,84,211)',
  sidebarBg: 'rgb(5,79,87)',
  sidebarBg2: 'rgb(6,70,77)',
  sidebarText: 'rgb(160,206,212)',
  sidebarActive: alpha('#ffffff', 0.16),
  sidebarBorder: alpha('#ffffff', 0.09),
}

const dark = {
  bg: '#0b1116',
  paper: '#121b22',
  surfaceSubtle: '#18242c',
  surfaceRaised: '#1d2a33',
  border: '#243038',
  textPrimary: '#eaf1f5',
  textSecondary: '#a4b4c0',
  textTertiary: '#71828f',
  brand: 'rgb(10,166,184)',
  brandText: '#3fcfdb',
  brandSubtle: alpha('rgb(10,166,184)', 0.15),
  green: 'rgb(20,180,138)',
  greenDark: 'rgb(16,152,116)',
  blue: 'rgb(76,144,242)',
  orange: 'rgb(246,188,86)',
  red: 'rgb(237,85,84)',
  purple: 'rgb(138,97,241)',
  sidebarBg: '#070c10',
  sidebarBg2: '#0c131a',
  sidebarText: '#8395a1',
  sidebarActive: alpha('rgb(10,166,184)', 0.16),
  sidebarBorder: '#161f27',
}

export function createAppTheme(mode: AppMode): Theme {
  const t = mode === 'dark' ? dark : light
  return createTheme({
    palette: {
      mode,
      primary: { main: t.green, dark: t.greenDark, contrastText: '#ffffff' },
      secondary: { main: t.brand },
      error: { main: t.red },
      warning: { main: t.orange },
      info: { main: t.blue },
      success: { main: t.green },
      background: { default: t.bg, paper: t.paper },
      text: { primary: t.textPrimary, secondary: t.textSecondary, disabled: t.textTertiary },
      divider: t.border,
      brand: { main: t.brand, text: t.brandText, subtle: t.brandSubtle },
      surface: { subtle: t.surfaceSubtle, raised: t.surfaceRaised },
      sidebar: {
        bg: t.sidebarBg, bg2: t.sidebarBg2, text: t.sidebarText,
        textActive: '#ffffff', activeBg: t.sidebarActive, border: t.sidebarBorder,
      },
    },
    typography: {
      fontFamily: FONT_BODY,
      h1: { fontFamily: FONT_DISPLAY, fontWeight: 800, letterSpacing: '-0.5px' },
      h2: { fontFamily: FONT_DISPLAY, fontWeight: 800, letterSpacing: '-0.3px' },
      h3: { fontFamily: FONT_DISPLAY, fontWeight: 700, letterSpacing: '-0.2px' },
      h4: { fontFamily: FONT_DISPLAY, fontWeight: 700 },
      h5: { fontFamily: FONT_DISPLAY, fontWeight: 700 },
      h6: { fontFamily: FONT_DISPLAY, fontWeight: 700 },
      button: { textTransform: 'none', fontWeight: 700 },
    },
    shape: { borderRadius: 8 },
    components: {
      MuiButton: {
        defaultProps: { disableElevation: true },
        styleOverrides: { root: { borderRadius: 7 } },
      },
      MuiPaper: {
        styleOverrides: {
          root: { backgroundImage: 'none' },
          outlined: { borderColor: t.border },
        },
      },
      MuiCard: {
        defaultProps: { variant: 'outlined' },
        styleOverrides: { root: { borderRadius: 10, borderColor: t.border } },
      },
      MuiChip: { styleOverrides: { root: { borderRadius: 5, fontWeight: 700 } } },
      MuiTableCell: {
        styleOverrides: { root: { borderColor: t.border } },
        defaultProps: {},
      },
      MuiOutlinedInput: {
        styleOverrides: {
          notchedOutline: { borderColor: t.border },
          root: { borderRadius: 7 },
        },
      },
    },
  })
}

// ---- Color mode context ----
interface ColorModeCtx { mode: AppMode; toggle: () => void; set: (m: AppMode) => void }
export const ColorModeContext = createContext<ColorModeCtx>({
  mode: 'dark', toggle: () => {}, set: () => {},
})
export const useColorMode = () => useContext(ColorModeContext)

export const MODE_STORAGE_KEY = 'korug.theme'
