import React, { useEffect, useState } from 'react'
import {
  Box, Card, CardContent, CardHeader, Typography, Button, Table, TableBody,
  TableCell, TableContainer, TableHead, TableRow, Chip, IconButton, Dialog,
  DialogTitle, DialogContent, DialogActions, TextField, MenuItem, Alert,
  CircularProgress, Tooltip, Stack, Switch, FormControlLabel,
} from '@mui/material'
import AddIcon from '@mui/icons-material/PersonAdd'
import DeleteIcon from '@mui/icons-material/Delete'
import KeyIcon from '@mui/icons-material/VpnKey'
import { userAPI } from '@/api/users'
import { useAuth } from '@/contexts/AuthContext'
import { User } from '@/types'
import { apiErrorMessage } from '@/utils/apiError'
import { formatDate } from '@/utils/formatters'

const ROLES = ['admin', 'viewer']

export const UsersPage: React.FC = () => {
  const { user: me } = useAuth()
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const [createOpen, setCreateOpen] = useState(false)
  const [form, setForm] = useState({ username: '', email: '', password: '', role: 'viewer' })

  const [resetFor, setResetFor] = useState<User | null>(null)
  const [newPassword, setNewPassword] = useState('')
  const [deleteFor, setDeleteFor] = useState<User | null>(null)

  const load = async () => {
    try {
      setLoading(true)
      setUsers(await userAPI.list())
      setError(null)
    } catch (err) {
      setError(apiErrorMessage(err, 'Failed to load users'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const flash = (msg: string) => { setSuccess(msg); setTimeout(() => setSuccess(null), 3000) }

  const handleCreate = async () => {
    try {
      await userAPI.create(form)
      setCreateOpen(false)
      setForm({ username: '', email: '', password: '', role: 'viewer' })
      flash('User created')
      load()
    } catch (err) {
      setError(apiErrorMessage(err, 'Failed to create user'))
    }
  }

  const handleToggleActive = async (u: User) => {
    try {
      const updated = await userAPI.update(u.id, { is_active: !u.is_active })
      setUsers((prev) => prev.map((x) => (x.id === u.id ? updated : x)))
    } catch (err) {
      setError(apiErrorMessage(err, 'Failed to update user'))
    }
  }

  const handleRoleChange = async (u: User, role: string) => {
    try {
      const updated = await userAPI.update(u.id, { role })
      setUsers((prev) => prev.map((x) => (x.id === u.id ? updated : x)))
      flash(`${u.username} is now ${role}`)
    } catch (err) {
      setError(apiErrorMessage(err, 'Failed to change role'))
    }
  }

  const handleReset = async () => {
    if (!resetFor) return
    try {
      await userAPI.resetPassword(resetFor.id, newPassword)
      setResetFor(null)
      setNewPassword('')
      flash('Password reset')
    } catch (err) {
      setError(apiErrorMessage(err, 'Failed to reset password'))
    }
  }

  const handleDelete = async () => {
    if (!deleteFor) return
    try {
      await userAPI.remove(deleteFor.id)
      setDeleteFor(null)
      flash('User deleted')
      load()
    } catch (err) {
      setError(apiErrorMessage(err, 'Failed to delete user'))
    }
  }

  if (loading) {
    return <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}><CircularProgress /></Box>
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4">Users</Typography>
          <Typography variant="body2" color="text.secondary">Manage who can access Körüg and what they can do.</Typography>
        </Box>
        <Button variant="contained" startIcon={<AddIcon />} onClick={() => setCreateOpen(true)}>Add User</Button>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>{error}</Alert>}
      {success && <Alert severity="success" sx={{ mb: 2 }}>{success}</Alert>}

      <Card>
        <CardContent sx={{ p: 0 }}>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>User</TableCell>
                  <TableCell>Role</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Last Login</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {users.map((u) => {
                  const isSelf = u.username === me?.username
                  return (
                    <TableRow key={u.id} hover>
                      <TableCell>
                        <Typography variant="subtitle2">{u.username}{isSelf && ' (you)'}</Typography>
                        <Typography variant="caption" color="text.secondary">{u.email}</Typography>
                      </TableCell>
                      <TableCell sx={{ width: 140 }}>
                        <TextField
                          select size="small" value={u.role} disabled={isSelf}
                          onChange={(e) => handleRoleChange(u, e.target.value)}
                          sx={{ minWidth: 110 }}
                        >
                          {ROLES.map((r) => <MenuItem key={r} value={r}>{r}</MenuItem>)}
                        </TextField>
                      </TableCell>
                      <TableCell>
                        <FormControlLabel
                          control={<Switch checked={u.is_active} disabled={isSelf} onChange={() => handleToggleActive(u)} size="small" />}
                          label={<Chip size="small" label={u.is_active ? 'Active' : 'Disabled'} color={u.is_active ? 'success' : 'default'} />}
                        />
                      </TableCell>
                      <TableCell><Typography variant="body2" color="text.secondary">{formatDate(u.last_login)}</Typography></TableCell>
                      <TableCell align="right">
                        <Tooltip title="Reset password">
                          <IconButton size="small" onClick={() => setResetFor(u)}><KeyIcon fontSize="small" /></IconButton>
                        </Tooltip>
                        <Tooltip title={isSelf ? 'You cannot delete yourself' : 'Delete user'}>
                          <span>
                            <IconButton size="small" color="error" disabled={isSelf} onClick={() => setDeleteFor(u)}>
                              <DeleteIcon fontSize="small" />
                            </IconButton>
                          </span>
                        </Tooltip>
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      {/* Create user */}
      <Dialog open={createOpen} onClose={() => setCreateOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Add User</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField label="Username" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} fullWidth />
            <TextField label="Email" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} fullWidth />
            <TextField label="Password" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} helperText="At least 8 characters" fullWidth />
            <TextField select label="Role" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} fullWidth>
              {ROLES.map((r) => <MenuItem key={r} value={r}>{r}</MenuItem>)}
            </TextField>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleCreate}>Create</Button>
        </DialogActions>
      </Dialog>

      {/* Reset password */}
      <Dialog open={Boolean(resetFor)} onClose={() => setResetFor(null)} maxWidth="xs" fullWidth>
        <DialogTitle>Reset password</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Set a new password for <b>{resetFor?.username}</b>.
          </Typography>
          <TextField label="New password" type="password" fullWidth value={newPassword} onChange={(e) => setNewPassword(e.target.value)} helperText="At least 8 characters" />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setResetFor(null)}>Cancel</Button>
          <Button variant="contained" onClick={handleReset} disabled={newPassword.length < 8}>Reset</Button>
        </DialogActions>
      </Dialog>

      {/* Delete */}
      <Dialog open={Boolean(deleteFor)} onClose={() => setDeleteFor(null)} maxWidth="xs" fullWidth>
        <DialogTitle>Delete user</DialogTitle>
        <DialogContent>
          <Typography>Delete <b>{deleteFor?.username}</b>? This cannot be undone.</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteFor(null)}>Cancel</Button>
          <Button color="error" variant="contained" onClick={handleDelete}>Delete</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
