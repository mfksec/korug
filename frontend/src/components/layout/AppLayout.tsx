import React, { useState, useEffect, useCallback } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import {
  AppBar, Avatar, Badge, Box, Divider, Drawer, IconButton, InputBase, List, ListItemButton,
  ListItemIcon, ListItemText, Menu, MenuItem, Toolbar, Tooltip, Typography,
  useMediaQuery, useTheme, ListSubheader, alpha,
} from '@mui/material'
import MenuIcon from '@mui/icons-material/Menu'
import DashboardIcon from '@mui/icons-material/SpaceDashboard'
import LanIcon from '@mui/icons-material/Lan'
import SecurityIcon from '@mui/icons-material/GppMaybe'
import NotificationsIcon from '@mui/icons-material/NotificationsActive'
import PeopleIcon from '@mui/icons-material/People'
import ExtensionIcon from '@mui/icons-material/Extension'
import SettingsIcon from '@mui/icons-material/Settings'
import HistoryIcon from '@mui/icons-material/History'
import LightModeIcon from '@mui/icons-material/LightMode'
import DarkModeIcon from '@mui/icons-material/DarkMode'
import LogoutIcon from '@mui/icons-material/Logout'
import PersonIcon from '@mui/icons-material/Person'
import SearchIcon from '@mui/icons-material/Search'
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft'
import ChevronRightIcon from '@mui/icons-material/ChevronRight'
import { useAuth } from '@/contexts/AuthContext'
import { useColorMode } from '@/contexts/ColorModeContext'
import { alertAPI } from '@/api/alerts'

const DRAWER_WIDTH = 248
const RAIL_WIDTH = 76
const COLLAPSE_KEY = 'korug.sidebar.collapsed'

interface NavItem {
  label: string
  path: string
  icon: React.ReactNode
  adminOnly?: boolean
  section: 'Monitoring' | 'Administration'
}

const NAV_ITEMS: NavItem[] = [
  { label: 'Dashboard', path: '/dashboard', icon: <DashboardIcon />, section: 'Monitoring' },
  { label: 'Assets', path: '/assets', icon: <LanIcon />, section: 'Monitoring' },
  { label: 'Vulnerabilities', path: '/vulnerabilities', icon: <SecurityIcon />, section: 'Monitoring' },
  { label: 'Alerts', path: '/alerts', icon: <NotificationsIcon />, section: 'Monitoring' },
  { label: 'Users', path: '/users', icon: <PeopleIcon />, adminOnly: true, section: 'Administration' },
  { label: 'Integrations', path: '/integrations', icon: <ExtensionIcon />, section: 'Administration' },
  { label: 'Settings', path: '/settings', icon: <SettingsIcon />, section: 'Administration' },
  { label: 'Audit Logs', path: '/audit-logs', icon: <HistoryIcon />, section: 'Administration' },
]

export const AppLayout: React.FC = () => {
  const theme = useTheme()
  const isDesktop = useMediaQuery(theme.breakpoints.up('md'))
  const navigate = useNavigate()
  const location = useLocation()
  const { user, isAdmin, logout } = useAuth()
  const { mode, toggle } = useColorMode()
  const [mobileOpen, setMobileOpen] = useState(false)
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null)
  const [collapsed, setCollapsed] = useState<boolean>(() => localStorage.getItem(COLLAPSE_KEY) === '1')
  const [search, setSearch] = useState('')
  const [activeAlerts, setActiveAlerts] = useState(0)

  // Mini (icon-only) rail applies on desktop when collapsed; mobile drawer is always full.
  const mini = collapsed && isDesktop
  const railWidth = collapsed ? RAIL_WIDTH : DRAWER_WIDTH

  const visibleItems = NAV_ITEMS.filter((i) => !i.adminOnly || isAdmin)
  const sections = Array.from(new Set(visibleItems.map((i) => i.section)))

  const toggleCollapsed = () => {
    setCollapsed((c) => {
      localStorage.setItem(COLLAPSE_KEY, c ? '0' : '1')
      return !c
    })
  }

  const fetchAlertCount = useCallback(async () => {
    try {
      const stats = await alertAPI.getStats()
      setActiveAlerts(stats.active)
    } catch {
      /* best-effort badge */
    }
  }, [])

  useEffect(() => {
    fetchAlertCount()
    const id = window.setInterval(fetchAlertCount, 30000)
    return () => window.clearInterval(id)
  }, [fetchAlertCount])

  const go = (path: string) => {
    navigate(path)
    if (!isDesktop) setMobileOpen(false)
  }

  const submitSearch = () => {
    const term = search.trim()
    navigate(term ? `/assets?q=${encodeURIComponent(term)}` : '/assets')
    if (!isDesktop) setMobileOpen(false)
  }

  const handleLogout = async () => {
    setAnchorEl(null)
    await logout()
    navigate('/login')
  }

  const initials = (user?.username || '?').slice(0, 2).toUpperCase()

  const drawer = (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Toolbar sx={{ px: mini ? 0 : 2.5, justifyContent: mini ? 'center' : 'flex-start' }}>
        <Typography variant="h6" sx={{ fontWeight: 800, letterSpacing: '-0.02em', color: '#fff' }}>
          {mini ? '𐰚' : '𐰚 Körüg'}
        </Typography>
      </Toolbar>
      <Divider sx={{ borderColor: 'rgba(255,255,255,0.08)' }} />
      <Box sx={{ flexGrow: 1, overflowY: 'auto', overflowX: 'hidden', py: 1 }}>
        {sections.map((section) => (
          <List
            key={section}
            subheader={
              mini ? undefined : (
                <ListSubheader disableSticky sx={{ bgcolor: 'transparent', color: 'rgba(255,255,255,0.45)', fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                  {section}
                </ListSubheader>
              )
            }
          >
            {visibleItems.filter((i) => i.section === section).map((item) => {
              const selected = location.pathname === item.path
              const button = (
                <ListItemButton
                  key={item.path}
                  selected={selected}
                  onClick={() => go(item.path)}
                  sx={mini ? { justifyContent: 'center', mx: 1, px: 1.5 } : undefined}
                >
                  <ListItemIcon sx={{ minWidth: mini ? 0 : 38 }}>{item.icon}</ListItemIcon>
                  {!mini && (
                    <ListItemText primary={item.label} primaryTypographyProps={{ fontWeight: selected ? 700 : 500 }} />
                  )}
                </ListItemButton>
              )
              return mini ? (
                <Tooltip key={item.path} title={item.label} placement="right">{button}</Tooltip>
              ) : button
            })}
          </List>
        ))}
      </Box>
      {/* Collapse toggle (desktop only) */}
      <Box sx={{ display: { xs: 'none', md: 'block' }, p: 1 }}>
        <Divider sx={{ borderColor: 'rgba(255,255,255,0.08)', mb: 1 }} />
        <ListItemButton onClick={toggleCollapsed} sx={mini ? { justifyContent: 'center' } : undefined}>
          <ListItemIcon sx={{ minWidth: mini ? 0 : 38 }}>
            {collapsed ? <ChevronRightIcon /> : <ChevronLeftIcon />}
          </ListItemIcon>
          {!mini && <ListItemText primary="Collapse" primaryTypographyProps={{ fontWeight: 500 }} />}
        </ListItemButton>
      </Box>
    </Box>
  )

  const contentOffset = { md: `${railWidth}px` }
  const contentWidth = { md: `calc(100% - ${railWidth}px)` }

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: 'background.default' }}>
      <AppBar position="fixed" sx={{ width: contentWidth, ml: contentOffset, transition: 'width .2s ease, margin .2s ease' }}>
        <Toolbar sx={{ gap: 1 }}>
          <IconButton color="inherit" edge="start" onClick={() => setMobileOpen(true)} sx={{ mr: 1, display: { md: 'none' } }}>
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" sx={{ fontWeight: 700, color: 'text.primary', whiteSpace: 'nowrap', display: { xs: 'none', sm: 'block' } }}>
            {visibleItems.find((i) => i.path === location.pathname)?.label || 'Körüg'}
          </Typography>

          {/* Global search → Assets */}
          <Box
            sx={{
              ml: { sm: 2 },
              flexGrow: 1,
              maxWidth: 460,
              display: 'flex',
              alignItems: 'center',
              gap: 1,
              px: 1.5,
              height: 38,
              borderRadius: 2,
              bgcolor: (t) => alpha(t.palette.text.primary, t.palette.mode === 'dark' ? 0.06 : 0.04),
              border: (t) => `1px solid ${t.palette.divider}`,
            }}
          >
            <SearchIcon sx={{ fontSize: 18, color: 'text.secondary' }} />
            <InputBase
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') submitSearch() }}
              placeholder="Search subdomains…"
              sx={{ flexGrow: 1, fontSize: 14, color: 'text.primary' }}
            />
          </Box>

          <Box sx={{ flexGrow: { xs: 1, sm: 0 } }} />

          <Tooltip title="Alerts">
            <IconButton onClick={() => navigate('/alerts')} sx={{ color: 'text.secondary' }}>
              <Badge badgeContent={activeAlerts} color="error" max={99}>
                <NotificationsIcon />
              </Badge>
            </IconButton>
          </Tooltip>

          <Tooltip title={mode === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}>
            <IconButton onClick={toggle} sx={{ color: 'text.secondary' }}>
              {mode === 'dark' ? <LightModeIcon /> : <DarkModeIcon />}
            </IconButton>
          </Tooltip>

          <Tooltip title="Account">
            <IconButton onClick={(e) => setAnchorEl(e.currentTarget)} sx={{ ml: 0.5 }}>
              <Avatar sx={{ width: 34, height: 34, bgcolor: 'primary.main', fontSize: 14, fontWeight: 700 }}>
                {initials}
              </Avatar>
            </IconButton>
          </Tooltip>
          <Menu anchorEl={anchorEl} open={Boolean(anchorEl)} onClose={() => setAnchorEl(null)}
                transformOrigin={{ horizontal: 'right', vertical: 'top' }}
                anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}>
            <Box sx={{ px: 2, py: 1 }}>
              <Typography variant="subtitle2">{user?.username}</Typography>
              <Typography variant="caption" color="text.secondary">{user?.email}</Typography>
            </Box>
            <Divider />
            <MenuItem onClick={() => { setAnchorEl(null); navigate('/profile') }}>
              <ListItemIcon><PersonIcon fontSize="small" /></ListItemIcon> Profile
            </MenuItem>
            <MenuItem onClick={handleLogout}>
              <ListItemIcon><LogoutIcon fontSize="small" /></ListItemIcon> Logout
            </MenuItem>
          </Menu>
        </Toolbar>
      </AppBar>

      {/* Sidebar: permanent (collapsible) on desktop, temporary drawer on mobile */}
      <Box component="nav" sx={{ width: { md: railWidth }, flexShrink: { md: 0 }, transition: 'width .2s ease' }}>
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={() => setMobileOpen(false)}
          ModalProps={{ keepMounted: true }}
          sx={{ display: { xs: 'block', md: 'none' }, '& .MuiDrawer-paper': { width: DRAWER_WIDTH } }}
        >
          {drawer}
        </Drawer>
        <Drawer
          variant="permanent"
          open
          sx={{
            display: { xs: 'none', md: 'block' },
            '& .MuiDrawer-paper': { width: railWidth, boxSizing: 'border-box', overflowX: 'hidden', transition: 'width .2s ease' },
          }}
        >
          {drawer}
        </Drawer>
      </Box>

      {/* Main content */}
      <Box component="main" sx={{ flexGrow: 1, width: contentWidth, minWidth: 0, transition: 'width .2s ease' }}>
        <Toolbar />
        <Box sx={{ p: { xs: 2, sm: 3 } }}>
          <Outlet />
        </Box>
      </Box>
    </Box>
  )
}
