import React, { useState } from 'react'
import {
  Box, Card, CardContent, CardHeader, Typography, TextField, Button, Alert,
  Stack, Grid, Avatar, Chip, Divider,
} from '@mui/material'
import { useAuth } from '@/contexts/AuthContext'
import { userAPI } from '@/api/users'
import { apiErrorMessage } from '@/utils/apiError'
import { formatDate } from '@/utils/formatters'

export const ProfilePage: React.FC = () => {
  const { user, refreshUser } = useAuth()

  const [email, setEmail] = useState(user?.email || '')
  const [savingEmail, setSavingEmail] = useState(false)

  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [confirm, setConfirm] = useState('')
  const [savingPwd, setSavingPwd] = useState(false)

  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const flash = (msg: string) => { setSuccess(msg); setTimeout(() => setSuccess(null), 3000) }

  const saveEmail = async () => {
    setError(null)
    setSavingEmail(true)
    try {
      await userAPI.updateProfile(email)
      await refreshUser()
      flash('Profile updated')
    } catch (err) {
      setError(apiErrorMessage(err, 'Failed to update profile'))
    } finally {
      setSavingEmail(false)
    }
  }

  const changePassword = async () => {
    setError(null)
    if (next !== confirm) { setError('New passwords do not match'); return }
    if (next.length < 8) { setError('New password must be at least 8 characters'); return }
    setSavingPwd(true)
    try {
      await userAPI.changePassword(current, next)
      setCurrent(''); setNext(''); setConfirm('')
      flash('Password changed')
    } catch (err) {
      setError(apiErrorMessage(err, 'Failed to change password'))
    } finally {
      setSavingPwd(false)
    }
  }

  const initials = (user?.username || '?').slice(0, 2).toUpperCase()

  return (
    <Box>
      <Typography variant="h4" sx={{ mb: 3 }}>My Profile</Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>{error}</Alert>}
      {success && <Alert severity="success" sx={{ mb: 2 }}>{success}</Alert>}

      <Grid container spacing={3}>
        <Grid item xs={12} md={5}>
          <Card>
            <CardContent>
              <Stack direction="row" spacing={2} alignItems="center">
                <Avatar sx={{ width: 64, height: 64, bgcolor: 'primary.main', fontSize: 24, fontWeight: 700 }}>{initials}</Avatar>
                <Box>
                  <Typography variant="h6">{user?.username}</Typography>
                  <Chip size="small" label={user?.role} color={user?.role === 'admin' ? 'primary' : 'default'} sx={{ mt: 0.5 }} />
                </Box>
              </Stack>
              <Divider sx={{ my: 2 }} />
              <Stack spacing={1}>
                <Row label="Email" value={user?.email} />
                <Row label="Member since" value={formatDate(user?.created_at ?? null)} />
                <Row label="Last login" value={formatDate(user?.last_login ?? null)} />
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={7}>
          <Card sx={{ mb: 3 }}>
            <CardHeader title="Account details" />
            <CardContent>
              <Stack spacing={2}>
                <TextField label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} fullWidth />
                <Box>
                  <Button variant="contained" onClick={saveEmail} disabled={savingEmail || email === user?.email}>
                    {savingEmail ? 'Saving…' : 'Save changes'}
                  </Button>
                </Box>
              </Stack>
            </CardContent>
          </Card>

          <Card>
            <CardHeader title="Change password" />
            <CardContent>
              <Stack spacing={2}>
                <TextField label="Current password" type="password" value={current} onChange={(e) => setCurrent(e.target.value)} fullWidth />
                <TextField label="New password" type="password" value={next} onChange={(e) => setNext(e.target.value)} helperText="At least 8 characters" fullWidth />
                <TextField label="Confirm new password" type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} fullWidth />
                <Box>
                  <Button variant="contained" onClick={changePassword} disabled={savingPwd || !current || !next}>
                    {savingPwd ? 'Updating…' : 'Update password'}
                  </Button>
                </Box>
              </Stack>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  )
}

const Row: React.FC<{ label: string; value?: string | null }> = ({ label, value }) => (
  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
    <Typography variant="body2" color="text.secondary">{label}</Typography>
    <Typography variant="body2">{value || '—'}</Typography>
  </Box>
)
