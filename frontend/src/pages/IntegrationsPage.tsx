import React, { useEffect, useState } from 'react'
import {
  Box, Card, CardContent, CardHeader, Typography, TextField, Button, Alert,
  Stack, Grid, Switch, FormControlLabel, CircularProgress, Chip, Divider,
  InputAdornment, MenuItem,
} from '@mui/material'
import SendIcon from '@mui/icons-material/Send'
import SaveIcon from '@mui/icons-material/Save'
import { integrationAPI, IntegrationsResponse, RECON_KEY_FIELDS, type ReconKeyField, type ReconKeysUpdate } from '@/api/integrations'
import { useAuth } from '@/contexts/AuthContext'
import { apiErrorMessage } from '@/utils/apiError'

const RECON_KEY_LABELS: Record<ReconKeyField, string> = {
  shodan_api_key: 'Shodan API Key',
  virustotal_api_key: 'VirusTotal API Key',
  securitytrails_api_key: 'SecurityTrails API Key',
  binaryedge_api_key: 'BinaryEdge API Key',
  urlscan_api_key: 'urlscan.io API Key',
  censys_api_id: 'Censys API ID',
  censys_api_secret: 'Censys API Secret',
  nvd_api_key: 'NVD API Key (CVE lookups)',
}

export const IntegrationsPage: React.FC = () => {
  const { isAdmin } = useAuth()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  // Slack form state
  const [slackEnabled, setSlackEnabled] = useState(false)
  const [slackConfigured, setSlackConfigured] = useState(false)
  const [webhook, setWebhook] = useState('')

  // Email form state
  const [email, setEmail] = useState({
    enabled: false, smtp_host: '', smtp_port: 587, smtp_user: '',
    smtp_password: '', use_tls: true, from_address: '', to_addresses: '',
  })
  const [pwdConfigured, setPwdConfigured] = useState(false)

  // Discovery source API keys: typed values (write-only) + configured flags
  const [reconValues, setReconValues] = useState<Record<string, string>>({})
  const [reconConfigured, setReconConfigured] = useState<Record<string, boolean>>({})

  const [busy, setBusy] = useState<string | null>(null)

  const apply = (data: IntegrationsResponse) => {
    setSlackEnabled(data.slack.enabled)
    setSlackConfigured(data.slack.webhook_configured)
    setWebhook('')
    setEmail({
      enabled: data.email.enabled,
      smtp_host: data.email.smtp_host,
      smtp_port: data.email.smtp_port,
      smtp_user: data.email.smtp_user,
      smtp_password: '',
      use_tls: data.email.use_tls,
      from_address: data.email.from_address,
      to_addresses: data.email.to_addresses,
    })
    setPwdConfigured(data.email.password_configured)
    const configured: Record<string, boolean> = {}
    RECON_KEY_FIELDS.forEach((f) => { configured[f] = Boolean(data.recon_keys?.[`${f}_configured`]) })
    setReconConfigured(configured)
    setReconValues({})
  }

  const load = async () => {
    try {
      setLoading(true)
      apply(await integrationAPI.get())
      setError(null)
    } catch (err) {
      setError(apiErrorMessage(err, 'Failed to load integrations'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const flash = (msg: string) => { setSuccess(msg); setTimeout(() => setSuccess(null), 4000) }
  const fail = (err: unknown, fb: string) => setError(apiErrorMessage(err, fb))

  const saveSlack = async () => {
    setBusy('slack-save'); setError(null)
    try {
      const res = await integrationAPI.updateSlack({ enabled: slackEnabled, webhook_url: webhook || null })
      setSlackConfigured(res.webhook_configured); setWebhook('')
      flash('Slack settings saved')
    } catch (err) { fail(err, 'Failed to save Slack settings') } finally { setBusy(null) }
  }

  const testSlack = async () => {
    setBusy('slack-test'); setError(null)
    try { const r = await integrationAPI.testSlack(); flash(r.message) }
    catch (err) { fail(err, 'Slack test failed') } finally { setBusy(null) }
  }

  const saveEmail = async () => {
    setBusy('email-save'); setError(null)
    try {
      const res = await integrationAPI.updateEmail({
        enabled: email.enabled, smtp_host: email.smtp_host, smtp_port: Number(email.smtp_port),
        smtp_user: email.smtp_user, smtp_password: email.smtp_password || null,
        use_tls: email.use_tls, from_address: email.from_address, to_addresses: email.to_addresses,
      })
      setPwdConfigured(res.password_configured)
      setEmail((e) => ({ ...e, smtp_password: '' }))
      flash('Email settings saved')
    } catch (err) { fail(err, 'Failed to save email settings') } finally { setBusy(null) }
  }

  const testEmail = async () => {
    setBusy('email-test'); setError(null)
    try { const r = await integrationAPI.testEmail(); flash(r.message) }
    catch (err) { fail(err, 'Email test failed') } finally { setBusy(null) }
  }

  const saveReconKeys = async () => {
    setBusy('keys-save'); setError(null)
    try {
      // Send only fields the user typed; blanks keep the stored value.
      const payload: ReconKeysUpdate = {}
      RECON_KEY_FIELDS.forEach((f) => { if (reconValues[f]) payload[f] = reconValues[f] })
      const res = await integrationAPI.updateReconKeys(payload)
      const configured: Record<string, boolean> = {}
      RECON_KEY_FIELDS.forEach((f) => { configured[f] = Boolean(res[`${f}_configured`]) })
      setReconConfigured(configured); setReconValues({})
      flash('Discovery API keys saved')
    } catch (err) { fail(err, 'Failed to save API keys') } finally { setBusy(null) }
  }

  if (loading) {
    return <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}><CircularProgress /></Box>
  }

  return (
    <Box>
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4">Integrations</Typography>
        <Typography variant="body2" color="text.secondary">
          Send takeover alerts to Slack/email, and add API keys for extra discovery sources.
        </Typography>
      </Box>

      {!isAdmin && <Alert severity="info" sx={{ mb: 2 }}>Only admins can change integration settings.</Alert>}
      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>{error}</Alert>}
      {success && <Alert severity="success" sx={{ mb: 2 }}>{success}</Alert>}

      <Grid container spacing={3}>
        {/* Slack */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardHeader
              title={<Stack direction="row" spacing={1} alignItems="center"><span>💬 Slack</span>
                <Chip size="small" label={slackEnabled ? 'Enabled' : 'Disabled'} color={slackEnabled ? 'success' : 'default'} /></Stack>}
              subheader="Incoming webhook notifications"
            />
            <CardContent>
              <Stack spacing={2}>
                <FormControlLabel
                  control={<Switch checked={slackEnabled} disabled={!isAdmin} onChange={(e) => setSlackEnabled(e.target.checked)} />}
                  label="Enable Slack notifications"
                />
                <TextField
                  label="Webhook URL" fullWidth disabled={!isAdmin} value={webhook}
                  onChange={(e) => setWebhook(e.target.value)}
                  placeholder={slackConfigured ? '•••••••• (configured — leave blank to keep)' : 'https://hooks.slack.com/services/…'}
                  helperText={slackConfigured ? 'A webhook is already saved. Enter a new one to replace it.' : 'Create one in Slack → Incoming Webhooks'}
                />
                <Divider />
                <Stack direction="row" spacing={1}>
                  <Button variant="contained" startIcon={<SaveIcon />} disabled={!isAdmin || busy === 'slack-save'} onClick={saveSlack}>Save</Button>
                  <Button variant="outlined" startIcon={<SendIcon />} disabled={!isAdmin || !slackConfigured || busy === 'slack-test'} onClick={testSlack}>
                    {busy === 'slack-test' ? 'Sending…' : 'Send test'}
                  </Button>
                </Stack>
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        {/* Email */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardHeader
              title={<Stack direction="row" spacing={1} alignItems="center"><span>✉️ Email (SMTP)</span>
                <Chip size="small" label={email.enabled ? 'Enabled' : 'Disabled'} color={email.enabled ? 'success' : 'default'} /></Stack>}
              subheader="Send alerts over your SMTP server"
            />
            <CardContent>
              <Stack spacing={2}>
                <FormControlLabel
                  control={<Switch checked={email.enabled} disabled={!isAdmin} onChange={(e) => setEmail({ ...email, enabled: e.target.checked })} />}
                  label="Enable email notifications"
                />
                <Grid container spacing={2}>
                  <Grid item xs={8}>
                    <TextField label="SMTP host" fullWidth disabled={!isAdmin} value={email.smtp_host}
                      onChange={(e) => setEmail({ ...email, smtp_host: e.target.value })} placeholder="smtp.gmail.com" />
                  </Grid>
                  <Grid item xs={4}>
                    <TextField label="Port" type="number" fullWidth disabled={!isAdmin} value={email.smtp_port}
                      onChange={(e) => setEmail({ ...email, smtp_port: Number(e.target.value) })} />
                  </Grid>
                </Grid>
                <TextField label="SMTP username" fullWidth disabled={!isAdmin} value={email.smtp_user}
                  onChange={(e) => setEmail({ ...email, smtp_user: e.target.value })} />
                <TextField label="SMTP password" type="password" fullWidth disabled={!isAdmin} value={email.smtp_password}
                  onChange={(e) => setEmail({ ...email, smtp_password: e.target.value })}
                  placeholder={pwdConfigured ? '•••••••• (configured — leave blank to keep)' : ''}
                  helperText={pwdConfigured ? 'A password is already saved. Enter a new one to replace it.' : undefined} />
                <TextField select label="Encryption" fullWidth disabled={!isAdmin}
                  value={email.use_tls ? 'tls' : 'none'} onChange={(e) => setEmail({ ...email, use_tls: e.target.value === 'tls' })}>
                  <MenuItem value="tls">STARTTLS (587) / SSL (465)</MenuItem>
                  <MenuItem value="none">None</MenuItem>
                </TextField>
                <TextField label="From address" fullWidth disabled={!isAdmin} value={email.from_address}
                  onChange={(e) => setEmail({ ...email, from_address: e.target.value })} placeholder="korug@yourdomain.com" />
                <TextField label="Recipients" fullWidth disabled={!isAdmin} value={email.to_addresses}
                  onChange={(e) => setEmail({ ...email, to_addresses: e.target.value })}
                  placeholder="soc@yourdomain.com, oncall@yourdomain.com"
                  InputProps={{ startAdornment: <InputAdornment position="start">To:</InputAdornment> }}
                  helperText="Comma-separated" />
                <Divider />
                <Stack direction="row" spacing={1}>
                  <Button variant="contained" startIcon={<SaveIcon />} disabled={!isAdmin || busy === 'email-save'} onClick={saveEmail}>Save</Button>
                  <Button variant="outlined" startIcon={<SendIcon />} disabled={!isAdmin || busy === 'email-test'} onClick={testEmail}>
                    {busy === 'email-test' ? 'Sending…' : 'Send test'}
                  </Button>
                </Stack>
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        {/* Discovery API keys */}
        <Grid item xs={12}>
          <Card>
            <CardHeader
              title="🔑 Discovery API Keys"
              subheader="Optional keys unlock extra subdomain sources. Free sources (crt.sh, etc.) need no key. Stored server-side and write-only (masked on read)."
            />
            <CardContent>
              <Grid container spacing={2}>
                {RECON_KEY_FIELDS.map((f) => (
                  <Grid item xs={12} sm={6} md={4} key={f}>
                    <TextField
                      label={RECON_KEY_LABELS[f]} type="password" fullWidth disabled={!isAdmin}
                      value={reconValues[f] || ''}
                      onChange={(e) => setReconValues((v) => ({ ...v, [f]: e.target.value }))}
                      placeholder={reconConfigured[f] ? '•••••••• (configured — blank keeps it)' : 'Not set'}
                    />
                  </Grid>
                ))}
              </Grid>
              <Divider sx={{ my: 2 }} />
              <Stack direction="row" spacing={1} alignItems="center">
                <Button variant="contained" startIcon={<SaveIcon />} disabled={!isAdmin || busy === 'keys-save'} onClick={saveReconKeys}>
                  {busy === 'keys-save' ? 'Saving…' : 'Save keys'}
                </Button>
                <Typography variant="caption" color="text.secondary">
                  Censys needs both ID and Secret. Keys take effect on the next discovery run.
                </Typography>
              </Stack>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  )
}
