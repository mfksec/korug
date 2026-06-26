import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Box, TextField, Button, Typography, Alert, useTheme } from '@mui/material'
import ShieldOutlined from '@mui/icons-material/ShieldOutlined'
import RadarOutlined from '@mui/icons-material/RadarOutlined'
import { useAuth } from '@/hooks/useAuth'

interface LoginPageProps { onLoginSuccess: () => void }

export const LoginPage: React.FC<LoginPageProps> = () => {
  const theme = useTheme()
  const { login, isLoading, error } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('')
  const sb = theme.palette.sidebar

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const success = await login({ username, password })
    if (success) navigate('/dashboard')
  }

  const stat = (value: string, label: string) => (
    <Box>
      <Typography sx={{ fontFamily: '"Roboto Mono", monospace', fontWeight: 700, fontSize: 22, color: theme.palette.brand.text }}>{value}</Typography>
      <Typography sx={{ fontSize: 12, color: 'rgba(255,255,255,.5)' }}>{label}</Typography>
    </Box>
  )

  return (
    <Box sx={{ minHeight: '100vh', display: 'flex' }}>
      {/* Brand panel */}
      <Box sx={{ flex: 1.1, bgcolor: sb.bg, color: '#fff', p: 7, display: { xs: 'none', md: 'flex' }, flexDirection: 'column', justifyContent: 'space-between', position: 'relative', overflow: 'hidden' }}>
        <RadarOutlined sx={{ position: 'absolute', right: -120, top: -60, fontSize: 360, color: 'rgba(255,255,255,.05)' }} />
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.4, position: 'relative' }}>
          <Box sx={{ width: 34, height: 34, borderRadius: 2, bgcolor: theme.palette.brand.main, display: 'flex', alignItems: 'center', justifyContent: 'center' }}><ShieldOutlined sx={{ fontSize: 20 }} /></Box>
          <Typography sx={{ fontFamily: theme.typography.h4.fontFamily, fontWeight: 800, fontSize: 20 }}>Körüg</Typography>
        </Box>
        <Box sx={{ position: 'relative', maxWidth: 420 }}>
          <Typography sx={{ fontFamily: theme.typography.h3.fontFamily, fontWeight: 800, fontSize: 34, lineHeight: 1.15, mb: 2 }}>Find your exposed subdomains before attackers do.</Typography>
          <Typography sx={{ fontSize: 15, color: 'rgba(255,255,255,.62)', lineHeight: 1.6 }}>Continuous multi-source discovery, takeover detection with confidence scoring, and real-time Slack alerting — for your entire domain ecosystem.</Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 3.5, position: 'relative' }}>
          {stat('4', 'discovery sources')}
          {stat('95%', 'detection confidence')}
          {stat('24/7', 'monitoring')}
        </Box>
      </Box>

      {/* Form panel */}
      <Box sx={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', p: 5, bgcolor: 'background.default' }}>
        <Box component="form" onSubmit={handleSubmit} sx={{ width: '100%', maxWidth: 360 }}>
          <Typography variant="h4" sx={{ fontSize: 24, mb: 0.7 }}>Sign in</Typography>
          <Typography sx={{ color: 'text.disabled', fontSize: 14, mb: 3.5 }}>Welcome back. Enter your credentials to continue.</Typography>
          {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
          <Typography sx={{ fontSize: 13, fontWeight: 700, color: 'text.secondary', mb: 0.9 }}>Username</Typography>
          <TextField fullWidth size="small" value={username} onChange={(e) => setUsername(e.target.value)} disabled={isLoading} sx={{ mb: 2.2 }} />
          <Typography sx={{ fontSize: 13, fontWeight: 700, color: 'text.secondary', mb: 0.9 }}>Password</Typography>
          <TextField fullWidth size="small" type="password" value={password} onChange={(e) => setPassword(e.target.value)} disabled={isLoading} sx={{ mb: 3 }} />
          <Button fullWidth type="submit" variant="contained" color="primary" size="large" disabled={isLoading}>{isLoading ? 'Signing in…' : 'Sign in'}</Button>
          <Typography sx={{ textAlign: 'center', mt: 2.2, fontSize: 12, color: 'text.disabled' }}>Protected by JWT authentication · Rate limited</Typography>
        </Box>
      </Box>
    </Box>
  )
}
