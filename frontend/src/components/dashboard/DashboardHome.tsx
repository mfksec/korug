import React, { useState, useEffect } from 'react'
import {
  Box, Grid, Paper, TextField, Button, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, IconButton, Dialog, DialogTitle,
  DialogContent, DialogActions, Chip, Tooltip, Stack, FormControlLabel,
  Switch, Snackbar, Alert, Typography,
} from '@mui/material'
import DeleteIcon from '@mui/icons-material/Delete'
import AddIcon from '@mui/icons-material/Add'
import EditIcon from '@mui/icons-material/Edit'
import PlayArrowIcon from '@mui/icons-material/PlayArrow'
import VisibilityIcon from '@mui/icons-material/Visibility'
import DomainIcon from '@mui/icons-material/Domain'
import SecurityIcon from '@mui/icons-material/Security'
import { StatsCard } from './StatsCard'
import { LoadingSpinner } from '../common/LoadingSpinner'
import { DomainDetailDialog } from './DomainDetailDialog'
import { useDomains } from '@/hooks/useDomains'
import { formatDate } from '@/utils/formatters'
import { domainAPI, type DashboardStats } from '@/api/domains'
import { scanAPI } from '@/api/scans'
import { apiErrorMessage } from '@/utils/apiError'
import { Domain } from '@/types'

export const DashboardHome: React.FC = () => {
  const { domains, isLoading, fetchDomains, addDomain, deleteDomain, updateDomain } = useDomains()
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [toast, setToast] = useState<{ msg: string; sev: 'success' | 'error' } | null>(null)

  const [openAdd, setOpenAdd] = useState(false)
  const [newDomain, setNewDomain] = useState('')
  const [isAdding, setIsAdding] = useState(false)

  const [editDomain, setEditDomain] = useState<Domain | null>(null)
  const [editName, setEditName] = useState('')
  const [editEnabled, setEditEnabled] = useState(true)

  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null)
  const [scanning, setScanning] = useState<number | null>(null)
  const [detailDomain, setDetailDomain] = useState<Domain | null>(null)

  const fetchStats = async () => {
    try {
      setStats(await domainAPI.getDashboardStats())
    } catch (error) {
      console.error('Failed to fetch dashboard stats:', error)
    }
  }

  useEffect(() => {
    fetchDomains()
    fetchStats()
  }, [fetchDomains])

  const handleAddDomain = async () => {
    if (!newDomain.trim()) return
    setIsAdding(true)
    try {
      await addDomain(newDomain.trim())
      setNewDomain('')
      setOpenAdd(false)
      setToast({ msg: 'Domain added', sev: 'success' })
    } catch (err) {
      setToast({ msg: apiErrorMessage(err, 'Failed to add domain'), sev: 'error' })
    } finally {
      setIsAdding(false)
    }
  }

  const openEdit = (d: Domain) => {
    setEditDomain(d)
    setEditName(d.domain_name)
    setEditEnabled(d.enabled)
  }

  const handleSaveEdit = async () => {
    if (!editDomain) return
    try {
      await updateDomain(editDomain.id, { domain_name: editName.trim(), enabled: editEnabled })
      setEditDomain(null)
      setToast({ msg: 'Domain updated', sev: 'success' })
    } catch (err) {
      setToast({ msg: apiErrorMessage(err, 'Failed to update domain'), sev: 'error' })
    }
  }

  const handleScan = async (d: Domain) => {
    setScanning(d.id)
    try {
      await scanAPI.triggerScan(d.id)
      setToast({ msg: `Scan started for ${d.domain_name}. Results appear in a few minutes.`, sev: 'success' })
    } catch (err) {
      setToast({ msg: apiErrorMessage(err, 'Failed to start scan'), sev: 'error' })
    } finally {
      setScanning(null)
    }
  }

  const handleDeleteDomain = async (id: number) => {
    try {
      await deleteDomain(id)
      setDeleteConfirm(null)
      setToast({ msg: 'Domain deleted', sev: 'success' })
    } catch (err) {
      setToast({ msg: apiErrorMessage(err, 'Failed to delete domain'), sev: 'error' })
    }
  }

  return (
    <Box>
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <StatsCard title="Total Domains" value={stats?.total_domains ?? domains.length} icon={<DomainIcon />} isLoading={isLoading} />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatsCard title="Vulnerabilities" value={stats?.total_vulnerabilities ?? 0} icon={<SecurityIcon />} />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatsCard title="Active Scans" value={stats?.active_scans ?? 0} />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatsCard title="High Risk Domains" value={stats?.high_risk_domains ?? 0} />
        </Grid>
      </Grid>

      <Paper sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">Monitored Domains</Typography>
          <Button variant="contained" startIcon={<AddIcon />} onClick={() => setOpenAdd(true)}>Add Domain</Button>
        </Box>

        {isLoading ? (
          <LoadingSpinner />
        ) : domains.length === 0 ? (
          <Box sx={{ textAlign: 'center', py: 4 }}>
            <Typography color="text.secondary">No domains added yet. Add one to start monitoring.</Typography>
          </Box>
        ) : (
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow sx={{ backgroundColor: 'action.hover' }}>
                  <TableCell>Domain</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Last Scanned</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {domains.map((domain) => (
                  <TableRow key={domain.id} hover>
                    <TableCell sx={{ fontWeight: 500 }}>{domain.domain_name}</TableCell>
                    <TableCell>
                      <Chip size="small" label={domain.enabled ? 'Active' : 'Inactive'}
                            color={domain.enabled ? 'success' : 'default'} />
                    </TableCell>
                    <TableCell>{formatDate(domain.last_scanned)}</TableCell>
                    <TableCell align="right">
                      <Stack direction="row" spacing={0.5} justifyContent="flex-end">
                        <Tooltip title="Run scan">
                          <span>
                            <IconButton size="small" color="primary" disabled={scanning === domain.id}
                                        onClick={() => handleScan(domain)}>
                              <PlayArrowIcon fontSize="small" />
                            </IconButton>
                          </span>
                        </Tooltip>
                        <Tooltip title="View results">
                          <IconButton size="small" onClick={() => setDetailDomain(domain)}>
                            <VisibilityIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Edit">
                          <IconButton size="small" onClick={() => openEdit(domain)}>
                            <EditIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Delete">
                          <IconButton size="small" color="error" onClick={() => setDeleteConfirm(domain.id)}>
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      </Stack>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Paper>

      {/* Add Domain */}
      <Dialog open={openAdd} onClose={() => setOpenAdd(false)} fullWidth maxWidth="xs">
        <DialogTitle>Add New Domain</DialogTitle>
        <DialogContent>
          <TextField autoFocus margin="dense" label="Domain Name" fullWidth value={newDomain}
                     onChange={(e) => setNewDomain(e.target.value)} placeholder="example.com"
                     onKeyDown={(e) => { if (e.key === 'Enter') handleAddDomain() }} />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenAdd(false)}>Cancel</Button>
          <Button onClick={handleAddDomain} variant="contained" disabled={isAdding}>
            {isAdding ? 'Adding…' : 'Add'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Edit Domain */}
      <Dialog open={Boolean(editDomain)} onClose={() => setEditDomain(null)} fullWidth maxWidth="xs">
        <DialogTitle>Edit Domain</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField label="Domain Name" fullWidth value={editName} onChange={(e) => setEditName(e.target.value)} />
            <FormControlLabel
              control={<Switch checked={editEnabled} onChange={(e) => setEditEnabled(e.target.checked)} />}
              label="Enabled (included in scheduled scans)"
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditDomain(null)}>Cancel</Button>
          <Button onClick={handleSaveEdit} variant="contained" disabled={!editName.trim()}>Save</Button>
        </DialogActions>
      </Dialog>

      {/* Delete confirm */}
      <Dialog open={deleteConfirm !== null} onClose={() => setDeleteConfirm(null)}>
        <DialogTitle>Confirm Delete</DialogTitle>
        <DialogContent>Are you sure you want to delete this domain and its results?</DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteConfirm(null)}>Cancel</Button>
          <Button onClick={() => deleteConfirm !== null && handleDeleteDomain(deleteConfirm)} color="error" variant="contained">
            Delete
          </Button>
        </DialogActions>
      </Dialog>

      {/* Detail / results */}
      <DomainDetailDialog
        open={Boolean(detailDomain)}
        domainId={detailDomain?.id ?? null}
        domainName={detailDomain?.domain_name}
        onClose={() => setDetailDomain(null)}
      />

      <Snackbar open={Boolean(toast)} autoHideDuration={4000} onClose={() => setToast(null)}
                anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}>
        {toast ? <Alert severity={toast.sev} onClose={() => setToast(null)}>{toast.msg}</Alert> : undefined}
      </Snackbar>
    </Box>
  )
}
