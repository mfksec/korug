import React from 'react'
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  Box,
  Menu,
  MenuItem,
} from '@mui/material'
import { useNavigate, useLocation } from 'react-router-dom'
import AccountCircleIcon from '@mui/icons-material/AccountCircle'
import { useAuth } from '@/hooks/useAuth'

export const Navbar: React.FC = () => {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null)

  const handleMenu = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget)
  }

  const handleClose = () => {
    setAnchorEl(null)
  }

  const handleLogout = async () => {
    handleClose()
    await logout()
    navigate('/login')
  }

  const navItems = [
    { label: 'Dashboard', path: '/dashboard' },
    { label: 'Vulnerabilities', path: '/vulnerabilities' },
    { label: 'Alerts', path: '/alerts' },
    { label: 'Settings', path: '/settings' },
    { label: 'Audit Logs', path: '/audit-logs' },
  ]

  const isActive = (path: string) => location.pathname === path

  return (
    <AppBar position="static">
      <Toolbar>
        <Typography
          variant="h6"
          sx={{ flexGrow: 1, fontWeight: 'bold', cursor: 'pointer' }}
          onClick={() => navigate('/dashboard')}
        >
          🔍 Körüg
        </Typography>

        {/* Navigation Links */}
        <Box sx={{ display: 'flex', gap: 1, mr: 2 }}>
          {navItems.map((item) => (
            <Button
              key={item.path}
              color="inherit"
              onClick={() => navigate(item.path)}
              sx={{
                textTransform: 'none',
                borderBottom: isActive(item.path) ? '2px solid white' : 'none',
                pb: isActive(item.path) ? '14px' : 'auto',
              }}
            >
              {item.label}
            </Button>
          ))}
        </Box>

        {/* User Menu */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Typography variant="body2">{user?.email}</Typography>
          <Button
            color="inherit"
            startIcon={<AccountCircleIcon />}
            onClick={handleMenu}
          >
            Menu
          </Button>
          <Menu
            anchorEl={anchorEl}
            open={Boolean(anchorEl)}
            onClose={handleClose}
          >
            <MenuItem onClick={handleLogout}>Logout</MenuItem>
          </Menu>
        </Box>
      </Toolbar>
    </AppBar>
  )
}
