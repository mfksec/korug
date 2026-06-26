# Körüg dashboard — UI redesign (React + MUI)

This package is a drop-in redesign of the `frontend/` UI: a clean visual
language with a darker security-tool feel, a persistent dark navigation rail,
a **light/dark toggle**, and **search / filter / sort** on every data table.
It uses only libraries already in your `package.json` (React 18, MUI v5,
recharts, react-router v6) — no new dependencies.

## What's included (paths relative to repo root)

**New**
- `frontend/src/styles/theme.ts` — theme factory (`createAppTheme(mode)`), color-mode context, custom palette (`brand`, `sidebar`, `surface`).
- `frontend/src/types/domain.ts` — UI-facing types (Domain, Subdomain, Vulnerability, Alert, AuditLog, risk levels…).
- `frontend/src/data/mock.ts` — mock data so it renders without the backend.
- `frontend/src/components/layout/AppLayout.tsx` — sidebar + topbar shell (theme toggle, search, scan, user menu).
- `frontend/src/components/common/Widgets.tsx` — StatCard, RiskChip, ConfidenceBar, Segmented, SearchField + meta helpers.
- `frontend/src/pages/DomainsPage.tsx`, `DomainDetailPage.tsx` — new screens.

**Replaced** (overwrite the originals)
- `frontend/src/App.tsx` — adds theme provider + nested layout routes (`/domains`, `/domains/:id`).
- `frontend/src/main.tsx` — providers now live in `App.tsx`.
- `frontend/src/pages/DashboardPage.tsx`, `VulnerabilitiesPage.tsx`, `AlertsPage.tsx`, `AuditLogsPage.tsx`, `SettingsPage.tsx`, `LoginPage.tsx`.

**Obsolete — delete after merging**
- `frontend/src/components/common/Navbar.tsx`
- `frontend/src/components/dashboard/DashboardHome.tsx`
- `frontend/src/components/dashboard/StatsCard.tsx`

## Wiring to the backend

Pages currently import from `@/data/mock`. Swap each for the matching `@/api/*`
call when ready, e.g. in `DomainsPage.tsx`:

```ts
// import { mockDomains } from '@/data/mock'
import { domainsApi } from '@/api/domains'
const [domains, setDomains] = useState<Domain[]>([])
useEffect(() => { domainsApi.list().then(setDomains) }, [])
```

The redesigned `Domain` type adds `subdomain_count`, `open_vulnerabilities`,
`risk`, and `source_count`. Either add these to the API response or derive them
client-side from subdomains/vulnerabilities.

## Run it

```bash
cd frontend
npm install
npm run dev      # http://localhost:3000
npm run lint     # passes clean
```

## Push to GitHub

```bash
# from the repo root, on a new branch
git checkout -b ui-redesign
# copy the files from this package into frontend/src/ (overwriting where noted),
# then delete the three obsolete files listed above
git add frontend/src
git commit -m "feat(ui): redesign dashboard — new theme, dark mode, domains, search/filter/sort"
git push -u origin ui-redesign
# open a PR for ui-redesign -> main
```
