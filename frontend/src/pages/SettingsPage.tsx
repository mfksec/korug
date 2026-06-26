import { useState } from 'react'
import {
  Box, Card, Avatar, Typography, Button, TextField, Grid, Divider, Switch,
  Slider, useTheme, Snackbar, Alert,
} from '@mui/material'
import PersonOutline from '@mui/icons-material/PersonOutline'
import VpnKeyOutlined from '@mui/icons-material/VpnKeyOutlined'
import ChatOutlined from '@mui/icons-material/ChatOutlined'
import RadarOutlined from '@mui/icons-material/RadarOutlined'
import SearchOutlined from '@mui/icons-material/SearchOutlined'
import PublicOutlined from '@mui/icons-material/PublicOutlined'
import { FONT_MONO } from '@/styles/theme'
import { TintChip, Segmented } from '@/components/common/Widgets'

type Tab = 'profile' | 'api' | 'integrations' | 'scanning'
const TABS: { key: Tab; label: string; icon: React.ReactNode }[] = [
  { key: 'profile', label: 'Profile', icon: <PersonOutline sx={{ fontSize: 18 }} /> },
  { key: 'api', label: 'API keys', icon: <VpnKeyOutlined sx={{ fontSize: 18 }} /> },
  { key: 'integrations', label: 'Integrations', icon: <ChatOutlined sx={{ fontSize: 18 }} /> },
  { key: 'scanning', label: 'Scanning', icon: <RadarOutlined sx={{ fontSize: 18 }} /> },
]

const tint = (color: string, mode: string) =>
  mode === 'dark' ? color.replace('rgb(', 'rgba(').replace(')', ',0.16)') : color.replace('rgb(', 'rgba(').replace(')', ',0.12)')

export function SettingsPage() {
  const theme = useTheme()
  const [tab, setTab] = useState<Tab>('profile')
  const [toast, setToast] = useState('')
  const [notify, setNotify] = useState({ takeover: true, orphan: true, newsub: false, scandone: true })
  const [schedule, setSchedule] = useState<'manual' | 'daily' | 'weekly'>('daily')
  const [sources, setSources] = useState({ subfinder: true, amass: true, shodan: true, urlscan: false })
  const save = () => setToast('Settings saved')

  const label = (t: string) => <Typography sx={{ fontSize: 13, fontWeight: 700, color: 'text.secondary', mb: 0.8 }}>{t}</Typography>

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
              <Avatar sx={{ width: 64, height: 64, bgcolor: theme.palette.brand.main, fontWeight: 800, fontSize: 24 }}>AD</Avatar>
              <Box>
                <Button variant="outlined" color="inherit" sx={{ borderColor: 'divider', color: 'text.secondary' }}>Change avatar</Button>
                <Typography sx={{ fontSize: 12, color: 'text.disabled', mt: 0.9 }}>PNG or JPG, max 1MB</Typography>
              </Box>
            </Box>
            <Grid container spacing={2} sx={{ mb: 2 }}>
              <Grid item xs={6}>{label('Username')}<TextField fullWidth size="small" defaultValue="admin" /></Grid>
              <Grid item xs={6}>{label('Email')}<TextField fullWidth size="small" defaultValue="admin@acme.com" /></Grid>
            </Grid>
            <Box sx={{ mb: 3 }}>{label('Role')}<TintChip label="Administrator" color="secondary" /></Box>
            <Divider sx={{ mb: 2.5 }} />
            <Typography sx={{ fontWeight: 700, fontSize: 14, mb: 1.8 }}>Change password</Typography>
            <Grid container spacing={2} sx={{ mb: 2.5 }}>
              <Grid item xs={6}>{label('New password')}<TextField fullWidth size="small" type="password" placeholder="••••••••" /></Grid>
              <Grid item xs={6}>{label('Confirm')}<TextField fullWidth size="small" type="password" placeholder="••••••••" /></Grid>
            </Grid>
            <Box sx={{ display: 'flex', gap: 1.2, justifyContent: 'flex-end', borderTop: 1, borderColor: 'divider', pt: 2.2 }}>
              <Button color="inherit" sx={{ color: 'text.secondary' }}>Cancel</Button>
              <Button variant="contained" color="primary" onClick={save}>Save changes</Button>
            </Box>
          </Card>
        )}

        {tab === 'api' && (
          <Box>
            <Typography variant="h5" sx={{ fontSize: 18 }}>API keys</Typography>
            <Typography sx={{ fontSize: 13, color: 'text.disabled', mb: 2.2 }}>Connect discovery sources. Keys are encrypted at rest and never logged.</Typography>
            {[
              { name: 'Shodan', desc: 'IP & port intelligence', icon: <RadarOutlined />, accent: theme.palette.info.main, masked: 'shdn_••••••••••••••••3kL9', status: 'Connected', sColor: 'success' as const },
              { name: 'urlscan.io', desc: 'URL archive & scan data', icon: <SearchOutlined />, accent: theme.palette.brand.text, masked: '', status: 'Not configured', sColor: 'default' as const },
              { name: 'Subfinder & Amass', desc: 'Passive & active enumeration', icon: <PublicOutlined />, accent: theme.palette.brand.main, masked: 'Built-in · no key required', status: 'Active', sColor: 'success' as const },
            ].map((k) => (
              <Card key={k.name} sx={{ p: 2.2, mb: 1.8, maxWidth: 680 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 1.8 }}>
                  <Avatar variant="rounded" sx={{ width: 38, height: 38, bgcolor: tint(k.accent, theme.palette.mode), color: k.accent }}>{k.icon}</Avatar>
                  <Box sx={{ flex: 1 }}>
                    <Typography sx={{ fontWeight: 700, fontSize: 15 }}>{k.name}</Typography>
                    <Typography sx={{ fontSize: 12.5, color: 'text.disabled' }}>{k.desc}</Typography>
                  </Box>
                  <TintChip label={k.status} color={k.sColor} dot={k.sColor !== 'default'} />
                </Box>
                <Box sx={{ display: 'flex', gap: 1.2 }}>
                  <TextField fullWidth size="small" defaultValue={k.masked} placeholder="Enter API key" sx={{ '& input': { fontFamily: FONT_MONO, fontSize: 13 } }} />
                  <Button variant="outlined" color="inherit" sx={{ borderColor: 'divider', color: 'text.secondary' }}>Test</Button>
                  <Button variant="contained" color="secondary" onClick={save}>Save</Button>
                </Box>
              </Card>
            ))}
          </Box>
        )}

        {tab === 'integrations' && (
          <Card sx={{ p: 3, maxWidth: 680 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 0.8 }}>
              <Avatar variant="rounded" sx={{ width: 38, height: 38, bgcolor: theme.palette.brand.subtle, color: theme.palette.brand.text }}><ChatOutlined /></Avatar>
              <Box>
                <Typography variant="h6" sx={{ fontSize: 17 }}>Slack notifications</Typography>
                <Typography sx={{ fontSize: 12.5, color: 'text.disabled' }}>Get real-time alerts when new issues are found.</Typography>
              </Box>
            </Box>
            <Box sx={{ my: 2.5 }}>{label('Webhook URL')}<TextField fullWidth size="small" defaultValue="https://hooks.slack.com/services/T0••••/B0••••/xY••••" sx={{ '& input': { fontFamily: FONT_MONO, fontSize: 13 } }} /></Box>
            <Typography sx={{ fontSize: 13, fontWeight: 700, color: 'text.secondary', mb: 1 }}>Notify me about</Typography>
            {[
              { key: 'takeover' as const, t: 'Takeover vulnerabilities', d: 'S3 buckets, CNAME & DNS orphans' },
              { key: 'orphan' as const, t: 'New high-risk subdomains', d: 'Newly exposed sensitive hosts' },
              { key: 'newsub' as const, t: 'All new subdomains', d: 'Every discovery (can be noisy)' },
              { key: 'scandone' as const, t: 'Scan completion', d: 'When a scheduled scan finishes' },
            ].map((n) => (
              <Box key={n.key} sx={{ display: 'flex', alignItems: 'center', gap: 1.5, py: 1.2, borderBottom: 1, borderColor: 'divider' }}>
                <Box sx={{ flex: 1 }}>
                  <Typography sx={{ fontSize: 13.5, fontWeight: 700 }}>{n.t}</Typography>
                  <Typography sx={{ fontSize: 12, color: 'text.disabled' }}>{n.d}</Typography>
                </Box>
                <Switch checked={notify[n.key]} onChange={(e) => setNotify({ ...notify, [n.key]: e.target.checked })} color="primary" />
              </Box>
            ))}
            <Box sx={{ display: 'flex', gap: 1.2, justifyContent: 'flex-end', mt: 2.2 }}>
              <Button variant="outlined" color="inherit" sx={{ borderColor: 'divider', color: 'text.secondary' }}>Send test</Button>
              <Button variant="contained" color="primary" onClick={save}>Save</Button>
            </Box>
          </Card>
        )}

        {tab === 'scanning' && (
          <Card sx={{ p: 3, maxWidth: 680 }}>
            <Typography variant="h5" sx={{ fontSize: 18 }}>Scanning configuration</Typography>
            <Typography sx={{ fontSize: 13, color: 'text.disabled', mb: 2.5 }}>Control how and when Körüg discovers and scans your domains.</Typography>
            <Box sx={{ mb: 2.8 }}>
              {label('Scan schedule')}
              <Segmented value={schedule} onChange={setSchedule} options={[{ value: 'manual', label: 'Manual' }, { value: 'daily', label: 'Daily' }, { value: 'weekly', label: 'Weekly' }]} />
            </Box>
            <Box sx={{ mb: 2.8 }}>
              {label('Discovery sources')}
              <Grid container spacing={1.2}>
                {[
                  { key: 'subfinder' as const, t: 'Subfinder', d: 'Fast passive enumeration' },
                  { key: 'amass' as const, t: 'Amass', d: 'Active & passive scanning' },
                  { key: 'shodan' as const, t: 'Shodan', d: 'IP / port intelligence' },
                  { key: 'urlscan' as const, t: 'urlscan.io', d: 'URL archive data' },
                ].map((s) => {
                  const on = sources[s.key]
                  return (
                    <Grid item xs={6} key={s.key}>
                      <Box onClick={() => setSources({ ...sources, [s.key]: !on })} sx={{
                        display: 'flex', alignItems: 'center', gap: 1.2, p: 1.5, borderRadius: 2, cursor: 'pointer',
                        border: 1, borderColor: on ? 'secondary.main' : 'divider', bgcolor: on ? theme.palette.brand.subtle : 'background.paper',
                      }}>
                        <Switch size="small" checked={on} color="secondary" sx={{ pointerEvents: 'none' }} />
                        <Box>
                          <Typography sx={{ fontSize: 13.5, fontWeight: 700 }}>{s.t}</Typography>
                          <Typography sx={{ fontSize: 11.5, color: 'text.disabled' }}>{s.d}</Typography>
                        </Box>
                      </Box>
                    </Grid>
                  )
                })}
              </Grid>
            </Box>
            <Box sx={{ mb: 1 }}>
              {label('Concurrency limit')}
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Slider defaultValue={8} min={1} max={20} valueLabelDisplay="auto" color="secondary" sx={{ flex: 1 }} />
              </Box>
            </Box>
            <Box sx={{ display: 'flex', justifyContent: 'flex-end', borderTop: 1, borderColor: 'divider', pt: 2.2, mt: 1.5 }}>
              <Button variant="contained" color="primary" onClick={save}>Save configuration</Button>
            </Box>
          </Card>
        )}
      </Box>

      <Snackbar open={!!toast} autoHideDuration={2600} onClose={() => setToast('')} anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}>
        <Alert severity="success" variant="filled" onClose={() => setToast('')}>{toast}</Alert>
      </Snackbar>
    </Box>
  )
}
