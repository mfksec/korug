import React, { useState, useEffect } from 'react'
import {
  Box,
  Grid,
  Paper,
  TextField,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material'
import DeleteIcon from '@mui/icons-material/Delete'
import AddIcon from '@mui/icons-material/Add'
import { StatsCard } from './StatsCard'
import { LoadingSpinner } from '../common/LoadingSpinner'
import { useDomains } from '@/hooks/useDomains'
import { formatDate } from '@/utils/formatters'
import { domainAPI, type DashboardStats } from '@/api/domains'
import DomainIcon from '@mui/icons-material/Domain'
import SecurityIcon from '@mui/icons-material/Security'

export const DashboardHome: React.FC = () => {
  const { domains, isLoading, fetchDomains, addDomain, deleteDomain } = useDomains()
  const [openDialog, setOpenDialog] = useState(false)
  const [newDomain, setNewDomain] = useState('')
  const [isAdding, setIsAdding] = useState(false)
  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null)
  const [stats, setStats] = useState<DashboardStats | null>(null)

  const fetchStats = async () => {
    try {
      const data = await domainAPI.getDashboardStats()
      setStats(data)
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
      setOpenDialog(false)
    } catch (error) {
      console.error('Failed to add domain:', error)
    } finally {
      setIsAdding(false)
    }
  }

  const handleDeleteDomain = async (id: number) => {
    try {
      await deleteDomain(id)
      setDeleteConfirm(null)
    } catch (error) {
      console.error('Failed to delete domain:', error)
    }
  }

  return (
    <Box>
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <StatsCard
            title="Total Domains"
            value={stats?.total_domains ?? domains.length}
            icon={<DomainIcon />}
            isLoading={isLoading}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatsCard
            title="Vulnerabilities"
            value={stats?.total_vulnerabilities ?? 0}
            icon={<SecurityIcon />}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatsCard
            title="Active Scans"
            value={stats?.active_scans ?? 0}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatsCard
            title="High Risk Domains"
            value={stats?.high_risk_domains ?? 0}
          />
        </Grid>
      </Grid>

      <Paper sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <h2>Monitored Domains</h2>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setOpenDialog(true)}
          >
            Add Domain
          </Button>
        </Box>

        {isLoading ? (
          <LoadingSpinner />
        ) : domains.length === 0 ? (
          <Box sx={{ textAlign: 'center', py: 4 }}>
            <p>No domains added yet. Start by adding a domain to monitor.</p>
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
                  <TableRow key={domain.id}>
                    <TableCell>{domain.domain_name}</TableCell>
                    <TableCell>
                      <span style={{ color: domain.enabled ? '#4caf50' : '#f44336' }}>
                        {domain.enabled ? '✓ Active' : '✗ Inactive'}
                      </span>
                    </TableCell>
                    <TableCell>{formatDate(domain.last_scanned)}</TableCell>
                    <TableCell align="right">
                      <IconButton
                        size="small"
                        onClick={() => setDeleteConfirm(domain.id)}
                        color="error"
                      >
                        <DeleteIcon />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Paper>

      {/* Add Domain Dialog */}
      <Dialog open={openDialog} onClose={() => setOpenDialog(false)}>
        <DialogTitle>Add New Domain</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Domain Name"
            type="text"
            fullWidth
            variant="standard"
            value={newDomain}
            onChange={(e) => setNewDomain(e.target.value)}
            placeholder="example.com"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDialog(false)}>Cancel</Button>
          <Button onClick={handleAddDomain} variant="contained" disabled={isAdding}>
            {isAdding ? 'Adding...' : 'Add'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteConfirm !== null} onClose={() => setDeleteConfirm(null)}>
        <DialogTitle>Confirm Delete</DialogTitle>
        <DialogContent>
          Are you sure you want to delete this domain?
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteConfirm(null)}>Cancel</Button>
          <Button
            onClick={() => deleteConfirm !== null && handleDeleteDomain(deleteConfirm)}
            color="error"
            variant="contained"
          >
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
