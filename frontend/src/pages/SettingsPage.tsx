import React, { useState, useEffect } from 'react'
import {
  Container,
  Box,
  Card,
  CardContent,
  CardHeader,
  Typography,
  Switch,
  FormControlLabel,
  Button,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  CircularProgress,
  IconButton,
  Tooltip,
  Grid,
} from '@mui/material'
import { Navbar } from '@/components/common/Navbar'
import { settingsAPI, type UserSettings, type APIKey } from '@/api/settings'
import DeleteIcon from '@mui/icons-material/Delete'
import ContentCopyIcon from '@mui/icons-material/ContentCopy'
import AddIcon from '@mui/icons-material/Add'

export const SettingsPage: React.FC = () => {
  const [settings, setSettings] = useState<UserSettings>({
    theme: 'light',
    notifications_enabled: true,
    email_alerts: true,
    scan_frequency: 'daily',
    export_format: 'json',
  })

  const [apiKeys, setApiKeys] = useState<APIKey[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [openNewKeyDialog, setOpenNewKeyDialog] = useState(false)
  const [newKeyName, setNewKeyName] = useState('')
  const [createdKey, setCreatedKey] = useState<APIKey | null>(null)

  // Fetch settings and API keys
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true)
        setError(null)
        const [settingsData, keysData] = await Promise.all([
          settingsAPI.getSettings(),
          settingsAPI.listApiKeys(),
        ])
        setSettings(settingsData.settings)
        setApiKeys(keysData)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load settings')
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  const handleSettingChange = (key: keyof UserSettings, value: string | boolean): void => {
    setSettings(prev => ({ ...prev, [key]: value }))
  }

  const handleSaveSettings = async () => {
    try {
      setSaving(true)
      setError(null)
      await settingsAPI.updateSettings(settings)
      setSuccess('Settings saved successfully!')
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  const handleCreateApiKey = async () => {
    if (!newKeyName.trim()) {
      setError('API key name is required')
      return
    }

    try {
      const newKey = await settingsAPI.createApiKey(newKeyName)
      setCreatedKey(newKey)
      setApiKeys(prev => [...prev, newKey])
      setNewKeyName('')
      setOpenNewKeyDialog(false)
      setSuccess('API key created successfully!')
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create API key')
    }
  }

  const handleRevokeApiKey = async (keyId: number): Promise<void> => {
    try {
      const updated = await settingsAPI.revokeApiKey(keyId)
      setApiKeys(prev => prev.map(k => (k.id === keyId ? updated : k)))
      setSuccess('API key revoked successfully!')
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to revoke API key')
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    setSuccess('Copied to clipboard!')
    setTimeout(() => setSuccess(null), 2000)
  }

  if (loading) {
    return (
      <Box>
        <Navbar />
        <Container maxWidth="lg" sx={{ py: 4, display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '500px' }}>
          <CircularProgress />
        </Container>
      </Box>
    )
  }

  return (
    <Box>
      <Navbar />
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Typography variant="h4" sx={{ mb: 4, fontWeight: 'bold' }}>
          Settings
        </Typography>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {success && (
          <Alert severity="success" sx={{ mb: 2 }}>
            {success}
          </Alert>
        )}

        <Grid container spacing={3}>
          {/* User Settings */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardHeader title="User Preferences" />
              <CardContent>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={settings.notifications_enabled}
                        onChange={(e) =>
                          handleSettingChange('notifications_enabled', e.target.checked)
                        }
                      />
                    }
                    label="Enable Notifications"
                  />

                  <FormControlLabel
                    control={
                      <Switch
                        checked={settings.email_alerts}
                        onChange={(e) =>
                          handleSettingChange('email_alerts', e.target.checked)
                        }
                      />
                    }
                    label="Email Alerts"
                  />

                  <FormControl fullWidth>
                    <InputLabel>Theme</InputLabel>
                    <Select
                      value={settings.theme}
                      label="Theme"
                      onChange={(e) =>
                        handleSettingChange('theme', e.target.value)
                      }
                    >
                      <MenuItem value="light">Light</MenuItem>
                      <MenuItem value="dark">Dark</MenuItem>
                    </Select>
                  </FormControl>

                  <FormControl fullWidth>
                    <InputLabel>Scan Frequency</InputLabel>
                    <Select
                      value={settings.scan_frequency}
                      label="Scan Frequency"
                      onChange={(e) =>
                        handleSettingChange('scan_frequency', e.target.value)
                      }
                    >
                      <MenuItem value="daily">Daily</MenuItem>
                      <MenuItem value="weekly">Weekly</MenuItem>
                      <MenuItem value="monthly">Monthly</MenuItem>
                    </Select>
                  </FormControl>

                  <FormControl fullWidth>
                    <InputLabel>Export Format</InputLabel>
                    <Select
                      value={settings.export_format}
                      label="Export Format"
                      onChange={(e) =>
                        handleSettingChange('export_format', e.target.value)
                      }
                    >
                      <MenuItem value="json">JSON</MenuItem>
                      <MenuItem value="csv">CSV</MenuItem>
                      <MenuItem value="pdf">PDF</MenuItem>
                    </Select>
                  </FormControl>

                  <Button
                    variant="contained"
                    onClick={handleSaveSettings}
                    disabled={saving}
                  >
                    {saving ? 'Saving...' : 'Save Settings'}
                  </Button>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          {/* API Keys */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardHeader
                title="API Keys"
                action={
                  <Button
                    startIcon={<AddIcon />}
                    onClick={() => setOpenNewKeyDialog(true)}
                    size="small"
                  >
                    New Key
                  </Button>
                }
              />
              <CardContent>
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow sx={{ bgcolor: '#f5f5f5' }}>
                        <TableCell>Name</TableCell>
                        <TableCell>Created</TableCell>
                        <TableCell>Status</TableCell>
                        <TableCell>Actions</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {apiKeys.length > 0 ? (
                        apiKeys.map(key => (
                          <TableRow key={key.id}>
                            <TableCell>{key.name}</TableCell>
                            <TableCell sx={{ fontSize: '0.85rem' }}>
                              {new Date(key.created_at).toLocaleDateString()}
                            </TableCell>
                            <TableCell>
                              {key.is_active ? (
                                <Typography color="success" variant="body2">
                                  Active
                                </Typography>
                              ) : (
                                <Typography color="error" variant="body2">
                                  Revoked
                                </Typography>
                              )}
                            </TableCell>
                            <TableCell>
                              <Tooltip title="Copy key">
                                <IconButton
                                  size="small"
                                  onClick={() => copyToClipboard(key.key)}
                                >
                                  <ContentCopyIcon fontSize="small" />
                                </IconButton>
                              </Tooltip>
                              {key.is_active && (
                                <Tooltip title="Revoke">
                                  <IconButton
                                    size="small"
                                    onClick={() => handleRevokeApiKey(key.id)}
                                  >
                                    <DeleteIcon fontSize="small" />
                                  </IconButton>
                                </Tooltip>
                              )}
                            </TableCell>
                          </TableRow>
                        ))
                      ) : (
                        <TableRow>
                          <TableCell colSpan={4} align="center" sx={{ py: 3 }}>
                            <Typography color="textSecondary">
                              No API keys yet
                            </Typography>
                          </TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </TableContainer>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* New API Key Dialog */}
        <Dialog open={openNewKeyDialog} onClose={() => setOpenNewKeyDialog(false)} maxWidth="sm" fullWidth>
          <DialogTitle>Create New API Key</DialogTitle>
          <DialogContent>
            <Box sx={{ pt: 2 }}>
              <TextField
                fullWidth
                label="API Key Name"
                value={newKeyName}
                onChange={(e) => setNewKeyName(e.target.value)}
                placeholder="e.g., CI/CD Integration"
                onKeyPress={(e) => {
                  if (e.key === 'Enter') {
                    handleCreateApiKey()
                  }
                }}
              />
              {createdKey && (
                <Alert severity="info" sx={{ mt: 2 }}>
                  <Typography variant="body2" sx={{ mb: 1 }}>
                    Your API key (shown only once):
                  </Typography>
                  <Typography
                    variant="body2"
                    sx={{
                      fontFamily: 'monospace',
                      bgcolor: '#f5f5f5',
                      p: 1,
                      borderRadius: 1,
                      wordBreak: 'break-all',
                      cursor: 'pointer',
                    }}
                    onClick={() => copyToClipboard(createdKey.key)}
                  >
                    {createdKey.key}
                  </Typography>
                </Alert>
              )}
            </Box>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setOpenNewKeyDialog(false)}>
              {createdKey ? 'Done' : 'Cancel'}
            </Button>
            {!createdKey && (
              <Button
                variant="contained"
                onClick={handleCreateApiKey}
              >
                Create
              </Button>
            )}
          </DialogActions>
        </Dialog>
      </Container>
    </Box>
  )
}
