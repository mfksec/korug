import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Box, Button, Card, Table, TableBody, TableCell, TableHead, TableRow, TableContainer,
  IconButton, Dialog, DialogTitle, DialogContent, DialogActions, TextField, MenuItem,
  Select, Typography, useTheme, Snackbar, Alert, LinearProgress, Tooltip,
} from '@mui/material'
import PersonAddOutlined from '@mui/icons-material/PersonAddAltOutlined'
import DeleteOutline from '@mui/icons-material/DeleteOutline'
import LockResetOutlined from '@mui/icons-material/LockResetOutlined'
import GroupOutlined from '@mui/icons-material/GroupOutlined'
import { FONT_MONO } from '@/styles/theme'
import { SearchField, TintChip, EmptyState } from '@/components/common/Widgets'
import { userAPI } from '@/api/users'
import { useAuth } from '@/hooks/useAuth'
import { timeAgo } from '@/data/apiAdapters'
import { apiErrorMessage } from '@/utils/apiError'
import { User } from '@/types'

export function UsersPage() {
  const theme = useTheme()
  const { user: me } = useAuth()
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [toast, setToast] = useState<{ msg: string; sev: 'success' | 'error' }>({ msg: '', sev: 'success' })

  const [addOpen, setAddOpen] = useState(false)
  const [form, setForm] = useState({ username: '', email: '', password: '', role: 'viewer' })
  const [saving, setSaving] = useState(false)

  const [resetFor, setResetFor] = useState<User | null>(null)
  const [newPwd, setNewPwd] = useState('')

  const ok = (msg: string) => setToast({ msg, sev: 'success' })
  const fail = (err: unknown, fallback: string) => setToast({ msg: apiErrorMessage(err, fallback), sev: 'error' })

  const load = useCallback(async () => {
    try {
      setUsers(await userAPI.list())
    } catch (err) {
      fail(err, 'Failed to load users')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const rows = useMemo(() => {
    const q = search.toLowerCase()
    return users.filter((u) => u.username.toLowerCase().includes(q) || u.email.toLowerCase().includes(q))
  }, [users, search])

  const createUser = async () => {
    const username = form.username.trim()
    const email = form.email.trim()
    if (username.length < 3) return setToast({ msg: 'Username must be at least 3 characters', sev: 'error' })
    if (!email.includes('@')) return setToast({ msg: 'Enter a valid email address', sev: 'error' })
    if (form.password.length < 8) return setToast({ msg: 'Password must be at least 8 characters', sev: 'error' })
    setSaving(true)
    try {
      await userAPI.create({ username, email, password: form.password, role: form.role })
      setAddOpen(false)
      setForm({ username: '', email: '', password: '', role: 'viewer' })
      ok(`User ${username} created`)
      load()
    } catch (err) {
      fail(err, 'Failed to create user')
    } finally {
      setSaving(false)
    }
  }

  const changeRole = async (u: User, role: string) => {
    try {
      await userAPI.update(u.id, { role })
      setUsers((list) => list.map((x) => (x.id === u.id ? { ...x, role } : x)))
      ok(`${u.username} is now ${role}`)
    } catch (err) {
      fail(err, 'Failed to change role')
    }
  }

  const toggleActive = async (u: User) => {
    try {
      const updated = await userAPI.update(u.id, { is_active: !u.is_active })
      setUsers((list) => list.map((x) => (x.id === u.id ? { ...x, is_active: updated.is_active } : x)))
      ok(updated.is_active ? `${u.username} activated` : `${u.username} deactivated`)
    } catch (err) {
      fail(err, 'Failed to update user')
    }
  }

  const resetPassword = async () => {
    if (!resetFor) return
    if (newPwd.length < 8) return setToast({ msg: 'Password must be at least 8 characters', sev: 'error' })
    try {
      await userAPI.resetPassword(resetFor.id, newPwd)
      ok(`Password reset for ${resetFor.username}`)
      setResetFor(null)
      setNewPwd('')
    } catch (err) {
      fail(err, 'Failed to reset password')
    }
  }

  const removeUser = async (u: User) => {
    try {
      await userAPI.remove(u.id)
      setUsers((list) => list.filter((x) => x.id !== u.id))
      ok(`User ${u.username} removed`)
    } catch (err) {
      fail(err, 'Failed to remove user')
    }
  }

  const th = { fontSize: 11.5, fontWeight: 700, letterSpacing: '.4px', textTransform: 'uppercase', color: 'text.disabled' } as const

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2.2, flexWrap: 'wrap' }}>
        <SearchField value={search} onChange={setSearch} placeholder="Search users…" sx={{ flex: 1, minWidth: 240, maxWidth: 340 }} />
        <Box sx={{ flex: 1 }} />
        <Button variant="contained" color="primary" startIcon={<PersonAddOutlined />} onClick={() => setAddOpen(true)}>Add user</Button>
      </Box>

      {loading && <LinearProgress sx={{ mb: 2, borderRadius: 1 }} />}

      {!loading && rows.length === 0 ? (
        <EmptyState
          icon={<GroupOutlined />}
          title={users.length === 0 ? 'No users yet' : 'No users match your search'}
          description={users.length === 0 ? 'Add a teammate and assign them an admin or viewer role.' : 'Try a different search term.'}
          action={users.length === 0 ? <Button variant="contained" startIcon={<PersonAddOutlined />} onClick={() => setAddOpen(true)}>Add user</Button> : undefined}
        />
      ) : (
        <Card>
          <TableContainer>
            <Table aria-label="Users" sx={{ '& td, & th': { borderColor: 'divider' } }}>
              <TableHead>
                <TableRow sx={{ bgcolor: 'surface.subtle' }}>
                  <TableCell sx={th}>User</TableCell>
                  <TableCell sx={th}>Role</TableCell>
                  <TableCell sx={th}>Status</TableCell>
                  <TableCell sx={th}>Last login</TableCell>
                  <TableCell align="right" sx={th}>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {rows.map((u) => {
                  const isSelf = me?.id === u.id
                  return (
                    <TableRow key={u.id} hover>
                      <TableCell>
                        <Typography sx={{ fontFamily: FONT_MONO, fontSize: 13.5, fontWeight: 600 }}>
                          {u.username}{isSelf && <Typography component="span" sx={{ ml: 1, fontSize: 11, color: 'text.disabled' }}>(you)</Typography>}
                        </Typography>
                        <Typography sx={{ fontSize: 12, color: 'text.disabled' }}>{u.email}</Typography>
                      </TableCell>
                      <TableCell>
                        <Select
                          size="small" value={u.role} disabled={isSelf}
                          onChange={(e) => changeRole(u, e.target.value)}
                          aria-label={`Role for ${u.username}`}
                          sx={{ fontSize: 13, fontWeight: 700, minWidth: 110, bgcolor: 'background.paper' }}
                        >
                          <MenuItem value="admin">Admin</MenuItem>
                          <MenuItem value="viewer">Viewer</MenuItem>
                        </Select>
                      </TableCell>
                      <TableCell>
                        <TintChip label={u.is_active ? 'Active' : 'Disabled'} color={u.is_active ? 'success' : 'default'} dot />
                      </TableCell>
                      <TableCell sx={{ fontSize: 13, color: 'text.disabled', whiteSpace: 'nowrap' }}>{timeAgo(u.last_login)}</TableCell>
                      <TableCell align="right">
                        <Tooltip title={u.is_active ? 'Deactivate' : 'Activate'}>
                          <span>
                            <Button size="small" variant="outlined" color="inherit" disabled={isSelf}
                              onClick={() => toggleActive(u)} sx={{ borderColor: 'divider', color: 'text.secondary', mr: 1 }}>
                              {u.is_active ? 'Disable' : 'Enable'}
                            </Button>
                          </span>
                        </Tooltip>
                        <Tooltip title="Reset password">
                          <IconButton size="small" onClick={() => { setResetFor(u); setNewPwd('') }} sx={{ color: 'text.disabled', '&:hover': { color: 'secondary.main' } }}>
                            <LockResetOutlined sx={{ fontSize: 18 }} />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title={isSelf ? 'You cannot delete your own account' : 'Delete user'}>
                          <span>
                            <IconButton size="small" disabled={isSelf} onClick={() => removeUser(u)}
                              sx={{ color: 'text.disabled', '&:hover': { color: 'error.main', bgcolor: theme.palette.error.main.replace('rgb(', 'rgba(').replace(')', ',0.12)') } }}>
                              <DeleteOutline sx={{ fontSize: 18 }} />
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
        </Card>
      )}

      {/* Add user */}
      <Dialog open={addOpen} onClose={() => setAddOpen(false)} PaperProps={{ sx: { borderRadius: 3, width: 460 } }}>
        <DialogTitle sx={{ fontFamily: theme.typography.h6.fontFamily, fontWeight: 700 }}>Add user</DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 1 }}>
          <TextField autoFocus label="Username" size="small" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} />
          <TextField label="Email" size="small" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
          <TextField label="Temporary password" size="small" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} helperText="At least 8 characters" />
          <Select size="small" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} aria-label="Role">
            <MenuItem value="viewer">Viewer — read-only</MenuItem>
            <MenuItem value="admin">Admin — full access</MenuItem>
          </Select>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2.5 }}>
          <Button onClick={() => setAddOpen(false)} sx={{ color: 'text.secondary' }}>Cancel</Button>
          <Button variant="contained" color="primary" startIcon={<PersonAddOutlined />} onClick={createUser} disabled={saving}>{saving ? 'Creating…' : 'Create user'}</Button>
        </DialogActions>
      </Dialog>

      {/* Reset password */}
      <Dialog open={!!resetFor} onClose={() => setResetFor(null)} PaperProps={{ sx: { borderRadius: 3, width: 420 } }}>
        <DialogTitle sx={{ fontFamily: theme.typography.h6.fontFamily, fontWeight: 700 }}>Reset password</DialogTitle>
        <DialogContent>
          <Typography sx={{ fontSize: 13, color: 'text.disabled', mb: 2 }}>Set a new password for <b>{resetFor?.username}</b>.</Typography>
          <TextField autoFocus fullWidth label="New password" size="small" type="password" value={newPwd} onChange={(e) => setNewPwd(e.target.value)} helperText="At least 8 characters" />
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2.5 }}>
          <Button onClick={() => setResetFor(null)} sx={{ color: 'text.secondary' }}>Cancel</Button>
          <Button variant="contained" color="primary" startIcon={<LockResetOutlined />} onClick={resetPassword}>Reset password</Button>
        </DialogActions>
      </Dialog>

      <Snackbar open={!!toast.msg} autoHideDuration={2800} onClose={() => setToast({ ...toast, msg: '' })} anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}>
        <Alert severity={toast.sev} variant="filled" onClose={() => setToast({ ...toast, msg: '' })}>{toast.msg}</Alert>
      </Snackbar>
    </Box>
  )
}
