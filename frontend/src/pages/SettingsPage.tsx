import { useCallback, useEffect, useState } from 'react'
import {
  Box, Card, Avatar, Typography, Button, TextField, Grid, Divider, Switch,
  Slider, useTheme, Snackbar, Alert, CircularProgress,
} from '@mui/material'
import PersonOutline from '@mui/icons-material/PersonOutline'
import VpnKeyOutlined from '@mui/icons-material/VpnKeyOutlined'
import ChatOutlined from '@mui/icons-material/ChatOutlined'
import RadarOutlined from '@mui/icons-material/RadarOutlined'
import { FONT_MONO } from '@/styles/theme'
import { TintChip, Segmented } from '@/components/common/Widgets'
import { useAuth } from '@/hooks/useAuth'
import { userAPI } from '@/api/users'
import { settingsAPI, type UserSettings } from '@/api/settings'
import {
  integrationAPI, type ReconKeyField, type IntegrationsResponse,
} from '@/api/integrations'
import { apiErrorMessage } from '@/utils/apiError'

type Tab = 'profile' | 'api' | 'integrations' | 'scanning'
const TABS: { key: Tab; label: string; icon: React.ReactNode }[] = [
  { key: 'profile', label: 'Profile', icon: <PersonOutline sx={{ fontSize: 18 }} /> },
  { key: 'api', label: 'API keys', icon: <VpnKeyOutlined sx={{ fontSize: 18 }} /> },
  { key: 'integrations', label: 'Integrations', icon: <ChatOutlined sx={{ fontSize: 18 }} /> },
  { key: 'scanning', label: 'Scanning', icon: <RadarOutlined sx={{ fontSize: 18 }} /> },
]

const RECON_SOURCES: { field: ReconKeyField; name: string; desc: string }[] = [
  { field: 'shodan_api_key', name: 'Shodan', desc: 'IP & port intelligence' },
  { field: 'virustotal_api_key', name: 'VirusTotal', desc: 'Passive DNS & reputation' },
  { field: 'securitytrails_api_key', name: 'SecurityTrails', desc: 'Historical DNS data' },
  { field: 'binaryedge_api_key', name: 'BinaryEdge', desc: 'Internet scan data' },
  { field: 'urlscan_api_key', name: 'urlscan.io', desc: 'URL archive & scan data' },
  { field: 'censys_api_id', name: 'Censys API ID', desc: 'Host & certificate search (ID)' },
  { field: 'censys_api_secret', name: 'Censys API Secret', desc: 'Host & certificate search (secret)' },
  { field: 'nvd_api_key', name: 'NVD API Key', desc: 'CVE lookups' },
]

export function SettingsPage() {
  const theme = useTheme()
  const { user, refreshUser } = useAuth()
  const [tab, setTab] = useState<Tab>('profile')
  const [toast, setToast] = useState<{ msg: string; sev: 'success' | 'error' }>({ msg: '', sev: 'success' })
  const flash = (msg: string, sev: 'success' | 'error' = 'success') => setToast({ msg, sev })

  // ----- Profile -----
  const [email, setEmail] = useState(user?.email || '')
  const [pwd, setPwd] = useState({ current: '', next: '', confirm: '' })
  const [savingProfile, setSavingProfile] = useState(false)

  const saveProfile = async () => {
    setSavingProfile(true)
    try {
      if (email && email !== user?.email) { await userAPI.updateProfile(email); await refreshUser() }
      if (pwd.next) {
        if (pwd.next !== pwd.confirm) throw new Error('New passwords do not match')
        if (pwd.next.length < 8) throw new Error('New password must be at least 8 characters')
        await userAPI.changePassword(pwd.current, pwd.next)
        setPwd({ current: '', next: '', confirm: '' })
      }
      flash('Profile saved')
    } catch (err) {
      flash(err instanceof Error ? err.message : apiErrorMessage(err, 'Failed to save profile'), 'error')
    } finally {
      setSavingProfile(false)
    }
  }

  // ----- Integrations (Slack) + API keys (recon sources) share /api/integrations -----
  const [integrations, setIntegrations] = useState<IntegrationsResponse | null>(null)
  const [slackEnabled, setSlackEnabled] = useState(false)
  const [webhook, setWebhook] = useState('')
  const [reconValues, setReconValues] = useState<Partial<Record<ReconKeyField, string>>>({})
  const [busy, setBusy] = useState('')

  const loadIntegrations = useCallback(async () => {
    try {
      const data = await integrationAPI.get()
      setIntegrations(data)
      setSlackEnabled(data.slack.enabled)
    } catch (err) {
      flash(apiErrorMessage(err, 'Failed to load integrations'), 'error')
    }
  }, [])

  useEffect(() => { loadIntegrations() }, [loadIntegrations])

  const reconConfigured = (f: ReconKeyField) => Boolean(integrations?.recon_keys?.[`${f}_configured`])

  const saveReconKey = async (f: ReconKeyField) => {
    const value = (reconValues[f] || '').trim()
    if (!value) return
    setBusy(f)
    try {
      await integrationAPI.updateReconKeys({ [f]: value })
      setReconValues((v) => ({ ...v, [f]: '' }))
      await loadIntegrations()
      flash('API key saved')
    } catch (err) {
      flash(apiErrorMessage(err, 'Failed to save key'), 'error')
    } finally {
      setBusy('')
    }
  }

  const saveSlack = async () => {
    setBusy('slack')
    try {
      await integrationAPI.updateSlack({ enabled: slackEnabled, webhook_url: webhook || null })
      setWebhook('')
      await loadIntegrations()
      flash('Slack settings saved')
    } catch (err) {
      flash(apiErrorMessage(err, 'Failed to save Slack settings'), 'error')
    } finally {
      setBusy('')
    }
  }

  const testSlack = async () => {
    setBusy('slack-test')
    try {
      const res = await integrationAPI.testSlack()
      flash(res.message || 'Test sent', res.status === 'success' ? 'success' : 'error')
    } catch (err) {
      flash(apiErrorMessage(err, 'Slack test failed'), 'error')
    } finally {
      setBusy('')
    }
  }

  // ----- Scanning (scan frequency persists via user settings) -----
  const [settings, setSettings] = useState<UserSettings | null>(null)
  const [savingScan, setSavingScan] = useState(false)
  useEffect(() => { settingsAPI.getSettings().then((r) => setSettings(r.settings)).catch(() => {}) }, [])

  const saveScanning = async () => {
    if (!settings) return
    setSavingScan(true)
    try {
      await settingsAPI.updateSettings(settings)
      flash('Scanning configuration saved')
    } catch (err) {
      flash(apiErrorMessage(err, 'Failed to save scanning configuration'), 'error')
    } finally {
      setSavingScan(false)
    }
  }

  const label = (t: string) => <Typography sx={{ fontSize: 13, fontWeight: 700, color: 'text.secondary', mb: 0.8 }}>{t}</Typography>
  const initials = (user?.username || '?').slice(0, 2).toUpperCase()

  return (
    <Box sx={{ display: 'flex', gap: 3, alignItems: 'flex-start' }}>
      <Box sx={{ width: 200, flexShrink: 0, position: 'sticky', top: 80 }}>
        {TABS.map((t) => {
          const active = tab === t.key
          return (
            <Box key={t.key} component="button" onClick={() => setTab(t.key)} sx={{
              display: 'flex', alignItems: 'center', gap: 1.4, width: '100%', px: 1.8, py: 1.4,
              border: 'none', borderRadius: 2, mb: 0.4, cursor: 'pointer', textAlign: 'left',
              fontSize: 13.5, fontWeight: 700, fontFamily: 'inherit',
              color: active ? theme.palette.brand.text : theme.palette.text.secondary,
              bgcolor: active ? theme.palette.brand.subtle : 'transparent',
              '&:hover': { bgcolor: active ? theme.palette.brand.subtle : theme.palette.surface.subtle },
            }}>
              {t.icon}{t.label}
            </Box>
          )
        })}
      </Box>

      <Box sx={{ flex: 1, minWidth: 0 }}>
        {tab === 'profile' && (
          <Card sx={{ p: 3, maxWidth: 620 }}>
            <Typography variant="h5" sx={{ fontSize: 18 }}>Profile</Typography>
            <Typography sx={{ fontSize: 13, color: 'text.disabled', mb: 2.5 }}>Manage your account details and credentials.</Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3, pb: 3, borderBottom: 1, borderColor: 'divider' }}>
              <Avatar sx={{ width: 64, height: 64, bgcolor: theme.palette.brand.main, fontWeight: 800, fontSize: 24 }}>{initials}</Avatar>
              <Box>
                <Typography sx={{ fontWeight: 700, fontSize: 16 }}>{user?.username}</Typography>
                <Box sx={{ mt: 0.6 }}><TintChip label={user?.role === 'admin' ? 'Administrator' : 'Viewer'} color="secondary" /></Box>
              </Box>
            </Box>
            <Grid container spacing={2} sx={{ mb: 2 }}>
              <Grid item xs={6}>{label('Username')}<TextField fullWidth size="small" value={user?.username || ''} disabled /></Grid>
              <Grid item xs={6}>{label('Email')}<TextField fullWidth size="small" value={email} onChange={(e) => setEmail(e.target.value)} /></Grid>
            </Grid>
            <Divider sx={{ mb: 2.5 }} />
            <Typography sx={{ fontWeight: 700, fontSize: 14, mb: 1.8 }}>Change password</Typography>
            <Grid container spacing={2} sx={{ mb: 2.5 }}>
              <Grid item xs={12}>{label('Current password')}<TextField fullWidth size="small" type="password" value={pwd.current} onChange={(e) => setPwd({ ...pwd, current: e.target.value })} placeholder="••••••••" /></Grid>
              <Grid item xs={6}>{label('New password')}<TextField fullWidth size="small" type="password" value={pwd.next} onChange={(e) => setPwd({ ...pwd, next: e.target.value })} placeholder="••••••••" /></Grid>
              <Grid item xs={6}>{label('Confirm')}<TextField fullWidth size="small" type="password" value={pwd.confirm} onChange={(e) => setPwd({ ...pwd, confirm: e.target.value })} placeholder="••••••••" /></Grid>
            </Grid>
            <Box sx={{ display: 'flex', gap: 1.2, justifyContent: 'flex-end', borderTop: 1, borderColor: 'divider', pt: 2.2 }}>
              <Button variant="contained" color="primary" onClick={saveProfile} disabled={savingProfile}>{savingProfile ? 'Saving…' : 'Save changes'}</Button>
            </Box>
          </Card>
        )}

        {tab === 'api' && (
          <Box>
            <Typography variant="h5" sx={{ fontSize: 18 }}>API keys</Typography>
            <Typography sx={{ fontSize: 13, color: 'text.disabled', mb: 2.2 }}>Connect discovery sources. Keys are encrypted at rest and never logged.</Typography>
            {RECON_SOURCES.map((s) => {
              const configured = reconConfigured(s.field)
              return (
                <Card key={s.field} sx={{ p: 2.2, mb: 1.8, maxWidth: 680 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 1.8 }}>
                    <Avatar variant="rounded" sx={{ width: 38, height: 38, bgcolor: theme.palette.brand.subtle, color: theme.palette.brand.text }}><VpnKeyOutlined /></Avatar>
                    <Box sx={{ flex: 1 }}>
                      <Typography sx={{ fontWeight: 700, fontSize: 15 }}>{s.name}</Typography>
                      <Typography sx={{ fontSize: 12.5, color: 'text.disabled' }}>{s.desc}</Typography>
                    </Box>
                    <TintChip label={configured ? 'Configured' : 'Not configured'} color={configured ? 'success' : 'default'} dot={configured} />
                  </Box>
                  <Box sx={{ display: 'flex', gap: 1.2 }}>
                    <TextField
                      fullWidth size="small" type="password"
                      value={reconValues[s.field] || ''}
                      onChange={(e) => setReconValues((v) => ({ ...v, [s.field]: e.target.value }))}
                      placeholder={configured ? 'Replace stored key' : 'Enter API key'}
                      sx={{ '& input': { fontFamily: FONT_MONO, fontSize: 13 } }}
                    />
                    <Button variant="contained" color="secondary" onClick={() => saveReconKey(s.field)} disabled={busy === s.field || !(reconValues[s.field] || '').trim()}>
                      {busy === s.field ? '…' : 'Save'}
                    </Button>
                  </Box>
                </Card>
              )
            })}
            <Card sx={{ p: 2.2, mb: 1.8, maxWidth: 680 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                <Avatar variant="rounded" sx={{ width: 38, height: 38, bgcolor: theme.palette.brand.subtle, color: theme.palette.brand.main }}><RadarOutlined /></Avatar>
                <Box sx={{ flex: 1 }}>
                  <Typography sx={{ fontWeight: 700, fontSize: 15 }}>Subfinder &amp; Amass</Typography>
                  <Typography sx={{ fontSize: 12.5, color: 'text.disabled' }}>Passive &amp; active enumeration · built-in, no key required</Typography>
                </Box>
                <TintChip label="Active" color="success" dot />
              </Box>
            </Card>
          </Box>
        )}

        {tab === 'integrations' && (
          <Card sx={{ p: 3, maxWidth: 680 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 0.8 }}>
              <Avatar variant="rounded" sx={{ width: 38, height: 38, bgcolor: theme.palette.brand.subtle, color: theme.palette.brand.text }}><ChatOutlined /></Avatar>
              <Box sx={{ flex: 1 }}>
                <Typography variant="h6" sx={{ fontSize: 17 }}>Slack notifications</Typography>
                <Typography sx={{ fontSize: 12.5, color: 'text.disabled' }}>Get real-time alerts when new issues are found.</Typography>
              </Box>
              <Switch checked={slackEnabled} onChange={(e) => setSlackEnabled(e.target.checked)} color="primary" />
            </Box>
            <Box sx={{ my: 2.5 }}>
              {label('Webhook URL')}
              <TextField
                fullWidth size="small"
                value={webhook}
                onChange={(e) => setWebhook(e.target.value)}
                placeholder={integrations?.slack.webhook_configured ? integrations.slack.webhook_url || 'Webhook configured — enter to replace' : 'https://hooks.slack.com/services/…'}
                sx={{ '& input': { fontFamily: FONT_MONO, fontSize: 13 } }}
              />
            </Box>
            <Box sx={{ display: 'flex', gap: 1.2, justifyContent: 'flex-end', mt: 1 }}>
              <Button variant="outlined" color="inherit" onClick={testSlack} disabled={busy === 'slack-test'} sx={{ borderColor: 'divider', color: 'text.secondary' }}>
                {busy === 'slack-test' ? 'Sending…' : 'Send test'}
              </Button>
              <Button variant="contained" color="primary" onClick={saveSlack} disabled={busy === 'slack'}>Save</Button>
            </Box>
          </Card>
        )}

        {tab === 'scanning' && (
          <Card sx={{ p: 3, maxWidth: 680 }}>
            <Typography variant="h5" sx={{ fontSize: 18 }}>Scanning configuration</Typography>
            <Typography sx={{ fontSize: 13, color: 'text.disabled', mb: 2.5 }}>Control how and when Körüg discovers and scans your domains.</Typography>
            {!settings ? (
              <CircularProgress size={22} />
            ) : (
              <>
                <Box sx={{ mb: 2.8 }}>
                  {label('Scan schedule')}
                  <Segmented
                    value={settings.scan_frequency}
                    onChange={(v) => setSettings({ ...settings, scan_frequency: v })}
                    options={[{ value: 'daily', label: 'Daily' }, { value: 'weekly', label: 'Weekly' }, { value: 'monthly', label: 'Monthly' }]}
                  />
                </Box>
                <Box sx={{ mb: 2.8 }}>
                  {label('Notifications')}
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, py: 1.2, borderBottom: 1, borderColor: 'divider' }}>
                    <Box sx={{ flex: 1 }}>
                      <Typography sx={{ fontSize: 13.5, fontWeight: 700 }}>In-app notifications</Typography>
                      <Typography sx={{ fontSize: 12, color: 'text.disabled' }}>Raise alerts in the dashboard for new findings</Typography>
                    </Box>
                    <Switch checked={settings.notifications_enabled} onChange={(e) => setSettings({ ...settings, notifications_enabled: e.target.checked })} color="primary" />
                  </Box>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, py: 1.2 }}>
                    <Box sx={{ flex: 1 }}>
                      <Typography sx={{ fontSize: 13.5, fontWeight: 700 }}>Email alerts</Typography>
                      <Typography sx={{ fontSize: 12, color: 'text.disabled' }}>Send a summary email when a scan finishes</Typography>
                    </Box>
                    <Switch checked={settings.email_alerts} onChange={(e) => setSettings({ ...settings, email_alerts: e.target.checked })} color="primary" />
                  </Box>
                </Box>
                <Box sx={{ mb: 1 }}>
                  {label('Default export format')}
                  <Segmented
                    value={settings.export_format}
                    onChange={(v) => setSettings({ ...settings, export_format: v })}
                    options={[{ value: 'json', label: 'JSON' }, { value: 'csv', label: 'CSV' }, { value: 'pdf', label: 'PDF' }]}
                  />
                </Box>
                <Box sx={{ mt: 2.8, mb: 1 }}>
                  {label('Concurrency limit (display)')}
                  <Slider defaultValue={8} min={1} max={20} valueLabelDisplay="auto" color="secondary" sx={{ flex: 1 }} disabled />
                  <Typography sx={{ fontSize: 11.5, color: 'text.disabled' }}>Configured server-side via environment.</Typography>
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'flex-end', borderTop: 1, borderColor: 'divider', pt: 2.2, mt: 1.5 }}>
                  <Button variant="contained" color="primary" onClick={saveScanning} disabled={savingScan}>{savingScan ? 'Saving…' : 'Save configuration'}</Button>
                </Box>
              </>
            )}
          </Card>
        )}
      </Box>

      <Snackbar open={!!toast.msg} autoHideDuration={3000} onClose={() => setToast({ ...toast, msg: '' })} anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}>
        <Alert severity={toast.sev} variant="filled" onClose={() => setToast({ ...toast, msg: '' })}>{toast.msg}</Alert>
      </Snackbar>
    </Box>
  )
}
