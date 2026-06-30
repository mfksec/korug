import { useCallback, useEffect, useState, MouseEvent } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import {
  Box, Drawer, AppBar, Toolbar, Typography, List, ListItemButton, ListItemIcon,
  ListItemText, Chip, IconButton, Button, Avatar, Menu, MenuItem, Divider,
  TextField, InputAdornment, LinearProgress, useTheme, Tooltip, Badge,
} from '@mui/material'
import SpaceDashboardOutlined from '@mui/icons-material/SpaceDashboardOutlined'
import PublicOutlined from '@mui/icons-material/PublicOutlined'
import GppMaybeOutlined from '@mui/icons-material/GppMaybeOutlined'
import NotificationsNoneOutlined from '@mui/icons-material/NotificationsNoneOutlined'
import ReceiptLongOutlined from '@mui/icons-material/ReceiptLongOutlined'
import DnsOutlined from '@mui/icons-material/DnsOutlined'
import TimelineOutlined from '@mui/icons-material/TimelineOutlined'
import SettingsOutlined from '@mui/icons-material/SettingsOutlined'
import ShieldOutlined from '@mui/icons-material/ShieldOutlined'
import RadarOutlined from '@mui/icons-material/RadarOutlined'
import GroupOutlined from '@mui/icons-material/GroupOutlined'
import SearchOutlined from '@mui/icons-material/SearchOutlined'
import LightModeOutlined from '@mui/icons-material/LightModeOutlined'
import DarkModeOutlined from '@mui/icons-material/DarkModeOutlined'
import KeyboardArrowDownOutlined from '@mui/icons-material/KeyboardArrowDownOutlined'
import LogoutOutlined from '@mui/icons-material/LogoutOutlined'
import { FONT_MONO, useColorMode } from '@/styles/theme'
import { useAuth } from '@/hooks/useAuth'
import { alertAPI } from '@/api/alerts'
import { scanAPI } from '@/api/scans'

const DRAWER_WIDTH = 236

const MONITORING = [
  { label: 'Dashboard', path: '/dashboard', icon: <SpaceDashboardOutlined /> },
  { label: 'Domains', path: '/domains', icon: <PublicOutlined /> },
  { label: 'Assets', path: '/assets', icon: <DnsOutlined /> },
  { label: 'Changes', path: '/changes', icon: <TimelineOutlined /> },
  { label: 'Vulnerabilities', path: '/vulnerabilities', icon: <GppMaybeOutlined /> },
  { label: 'Alerts', path: '/alerts', icon: <NotificationsNoneOutlined /> },
]

// Administration group — admin-only (gated in the nav + by route guards).
const ADMINISTRATION = [
  { label: 'Users', path: '/users', icon: <GroupOutlined /> },
  { label: 'Audit logs', path: '/audit-logs', icon: <ReceiptLongOutlined /> },
  { label: 'Settings', path: '/settings', icon: <SettingsOutlined /> },
]

const TITLES: Record<string, string> = Object.fromEntries(
  [...MONITORING, ...ADMINISTRATION].map((n) => [n.path, n.label]),
)

export function AppLayout() {
  const theme = useTheme()
  const navigate = useNavigate()
  const location = useLocation()
  const { mode, toggle } = useColorMode()
  const { user, logout, isAdmin } = useAuth()
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null)
  const [activeAlerts, setActiveAlerts] = useState(0)
  const [activeScans, setActiveScans] = useState(0)
  const [query, setQuery] = useState('')

  const submitSearch = () => {
    const q = query.trim()
    if (q) navigate(`/assets?q=${encodeURIComponent(q)}`)
  }
  const sb = theme.palette.sidebar

  const isActive = (path: string) =>
    location.pathname === path ||
    (path === '/domains' && location.pathname.startsWith('/domains/')) ||
    (path === '/assets' && location.pathname.startsWith('/subdomains/'))
  const title = TITLES[location.pathname] ||
    (location.pathname.startsWith('/domains/') ? 'Domain detail' :
      location.pathname.startsWith('/subdomains/') ? 'Subdomain detail' : 'Körüg')

  const refreshAlerts = useCallback(async () => {
    try { setActiveAlerts((await alertAPI.getStats()).active) } catch { /* best-effort */ }
  }, [])
  const refreshScans = useCallback(async () => {
    try { setActiveScans((await scanAPI.getActiveScans()).length) } catch { /* best-effort */ }
  }, [])

  useEffect(() => {
    refreshAlerts(); refreshScans()
    const a = window.setInterval(refreshAlerts, 30000)
    const s = window.setInterval(refreshScans, 5000)
    return () => { window.clearInterval(a); window.clearInterval(s) }
  }, [refreshAlerts, refreshScans])

  const handleLogout = async () => {
    setAnchorEl(null)
    await logout()
    navigate('/login')
  }

  const initials = (user?.username || '?').slice(0, 2).toUpperCase()

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: 'background.default' }}>
      {/* Skip link: first focusable element, visible only when focused. */}
      <Box
        component="a"
        href="#main-content"
        sx={{
          position: 'absolute', left: 8, top: -48, zIndex: (t) => t.zIndex.modal + 1,
          px: 2, py: 1, borderRadius: 1.5, bgcolor: 'background.paper', color: 'text.primary',
          border: 1, borderColor: 'divider', fontSize: 13, fontWeight: 700, textDecoration: 'none',
          transition: 'top .15s', '&:focus': { top: 8 },
        }}
      >
        Skip to content
      </Box>
      <Drawer
        variant="permanent"
        sx={{
          width: DRAWER_WIDTH, flexShrink: 0,
          '& .MuiDrawer-paper': { width: DRAWER_WIDTH, boxSizing: 'border-box', bgcolor: sb.bg, borderColor: sb.border, color: sb.text },
        }}
      >
        {/* Brand */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.4, p: 2.2, borderBottom: 1, borderColor: sb.border }}>
          <Box sx={{ width: 32, height: 32, borderRadius: 2, bgcolor: theme.palette.brand.main, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff' }}>
            <ShieldOutlined sx={{ fontSize: 19 }} />
          </Box>
          <Box>
            <Typography sx={{ fontFamily: theme.typography.h6.fontFamily, fontWeight: 800, fontSize: 17, color: sb.textActive, lineHeight: 1 }}>Körüg</Typography>
            <Typography sx={{ fontSize: 10, color: sb.text, letterSpacing: '.5px', textTransform: 'uppercase', mt: 0.3 }}>Attack surface monitor</Typography>
          </Box>
        </Box>

        <Box component="nav" aria-label="Primary navigation" sx={{ flex: 1, overflowY: 'auto' }}>
          {[
            { heading: 'Monitoring', items: MONITORING, show: true },
            { heading: 'Administration', items: ADMINISTRATION, show: isAdmin },
          ].filter((g) => g.show).map((group) => (
            <Box key={group.heading}>
              <Typography sx={{ px: 2.7, pt: 2, pb: 1, fontSize: 10.5, fontWeight: 700, letterSpacing: '.8px', textTransform: 'uppercase', color: sb.text, opacity: 0.7 }}>{group.heading}</Typography>
              <List sx={{ px: 1.2 }}>
                {group.items.map((item) => {
                  const active = isActive(item.path)
                  const badge = item.path === '/alerts' && activeAlerts > 0 ? activeAlerts : null
                  return (
                    <ListItemButton
                      key={item.path}
                      onClick={() => navigate(item.path)}
                      sx={{
                        borderRadius: 1.75, mb: 0.3, py: 1.1, color: active ? sb.textActive : sb.text,
                        bgcolor: active ? sb.activeBg : 'transparent',
                        boxShadow: active ? `inset 3px 0 0 ${theme.palette.brand.main}` : 'none',
                        '&:hover': { bgcolor: sb.activeBg, color: sb.textActive },
                      }}
                    >
                      <ListItemIcon sx={{ minWidth: 32, color: 'inherit', '& svg': { fontSize: 19 } }}>{item.icon}</ListItemIcon>
                      <ListItemText primary={item.label} primaryTypographyProps={{ fontSize: 13.5, fontWeight: active ? 700 : 500 }} />
                      {badge != null && (
                        <Chip label={badge} size="small" sx={{ height: 20, fontFamily: FONT_MONO, fontWeight: 700, fontSize: 11, bgcolor: theme.palette.error.main, color: '#fff' }} />
                      )}
                    </ListItemButton>
                  )
                })}
              </List>
            </Box>
          ))}
        </Box>

        {/* Live scan status (only while a discovery is running) */}
        {activeScans > 0 && (
          <Box sx={{ p: 1.5, borderTop: 1, borderColor: sb.border }}>
            <Box sx={{ bgcolor: sb.bg2, border: 1, borderColor: sb.border, borderRadius: 2, p: 1.5 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <RadarOutlined sx={{ fontSize: 15, color: theme.palette.brand.text, animation: 'spin 2.4s linear infinite', '@keyframes spin': { to: { transform: 'rotate(360deg)' } } }} />
                <Typography sx={{ fontSize: 12, fontWeight: 700, color: sb.textActive }}>
                  Scanning {activeScans} domain{activeScans > 1 ? 's' : ''}
                </Typography>
              </Box>
              <LinearProgress sx={{ height: 5, borderRadius: 3, bgcolor: 'rgba(255,255,255,.1)', '& .MuiLinearProgress-bar': { bgcolor: theme.palette.brand.main } }} />
            </Box>
          </Box>
        )}
      </Drawer>

      <Box sx={{ flexGrow: 1, minWidth: 0 }}>
        <AppBar
          position="sticky"
          elevation={0}
          sx={{ bgcolor: 'background.paper', color: 'text.primary', borderBottom: 1, borderColor: 'divider', backdropFilter: 'blur(8px)' }}
        >
          <Toolbar sx={{ gap: 2 }}>
            <Typography variant="h6" sx={{ fontSize: 18, whiteSpace: 'nowrap' }}>{title}</Typography>
            <Box sx={{ flex: 1, display: 'flex', justifyContent: 'center' }}>
              <TextField
                size="small"
                placeholder="Search domains, subdomains, hosts…"
                type="search"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') submitSearch() }}
                sx={{ width: '100%', maxWidth: 440, '& .MuiOutlinedInput-root': { bgcolor: 'background.default' } }}
                inputProps={{ 'aria-label': 'Search domains, subdomains, and hosts' }}
                InputProps={{ startAdornment: <InputAdornment position="start"><SearchOutlined sx={{ fontSize: 18, color: 'text.disabled' }} /></InputAdornment> }}
              />
            </Box>
            <Button variant="contained" color="primary" startIcon={<RadarOutlined />} onClick={() => navigate('/domains')}>Scan now</Button>
            <Tooltip title="Toggle theme">
              <IconButton onClick={toggle} aria-label={mode === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'} sx={{ border: 1, borderColor: 'divider', borderRadius: 1.75 }}>
                {mode === 'dark' ? <LightModeOutlined sx={{ fontSize: 19 }} /> : <DarkModeOutlined sx={{ fontSize: 19 }} />}
              </IconButton>
            </Tooltip>
            <Tooltip title="Alerts">
              <IconButton onClick={() => navigate('/alerts')} aria-label={`Alerts${activeAlerts > 0 ? `, ${activeAlerts} active` : ''}`} sx={{ border: 1, borderColor: 'divider', borderRadius: 1.75 }}>
                <Badge badgeContent={activeAlerts} color="error" max={99}>
                  <NotificationsNoneOutlined sx={{ fontSize: 19 }} />
                </Badge>
              </IconButton>
            </Tooltip>
            <Button onClick={(e: MouseEvent<HTMLElement>) => setAnchorEl(e.currentTarget)} aria-label="Account menu" aria-haspopup="true" sx={{ borderRadius: 20, border: 1, borderColor: 'divider', pl: 0.5, pr: 1, py: 0.5, minWidth: 0 }}>
              <Avatar sx={{ width: 28, height: 28, bgcolor: theme.palette.brand.main, fontSize: 12, fontWeight: 700 }}>{initials}</Avatar>
              <KeyboardArrowDownOutlined sx={{ fontSize: 16, color: 'text.disabled', ml: 0.5 }} />
            </Button>
            <Menu anchorEl={anchorEl} open={Boolean(anchorEl)} onClose={() => setAnchorEl(null)} anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }} transformOrigin={{ vertical: 'top', horizontal: 'right' }}>
              <Box sx={{ px: 2, py: 1, minWidth: 200 }}>
                <Typography sx={{ fontWeight: 700, fontSize: 14 }}>{user?.username}</Typography>
                <Typography sx={{ fontSize: 12, color: 'text.disabled' }}>{user?.email}</Typography>
                <Box sx={{ mt: 0.6 }}><Chip label={isAdmin ? 'Administrator' : 'Viewer'} size="small" sx={{ height: 20, fontWeight: 700, fontSize: 11 }} /></Box>
              </Box>
              <Divider />
              {isAdmin && (
                <MenuItem onClick={() => { setAnchorEl(null); navigate('/users') }}><GroupOutlined sx={{ fontSize: 18, mr: 1.5 }} />Users</MenuItem>
              )}
              {isAdmin && (
                <MenuItem onClick={() => { setAnchorEl(null); navigate('/audit-logs') }}><ReceiptLongOutlined sx={{ fontSize: 18, mr: 1.5 }} />Audit logs</MenuItem>
              )}
              <MenuItem onClick={() => { setAnchorEl(null); navigate('/settings') }}><SettingsOutlined sx={{ fontSize: 18, mr: 1.5 }} />Settings</MenuItem>
              <MenuItem onClick={handleLogout} sx={{ color: 'error.main' }}><LogoutOutlined sx={{ fontSize: 18, mr: 1.5 }} />Sign out</MenuItem>
            </Menu>
          </Toolbar>
        </AppBar>

        <Box component="main" id="main-content" tabIndex={-1} sx={{ p: 3.5, maxWidth: 1320, mx: 'auto', outline: 'none' }}>
          <Outlet />
        </Box>
      </Box>
    </Box>
  )
}
