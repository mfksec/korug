# Körüg Roadmap

This is a living document describing where Körüg is heading. It's intentionally
high-level — dates are aspirational, scope may shift, and community input is
welcome. Open an issue or discussion if you'd like to shape a direction or pick
up an item.

Körüg's north star is to be the **self-hosted control plane for External Attack
Surface Management**: a continuous loop of **Discover → Attribute → Enrich →
Assess → Prioritize → Alert → Verify**, built entirely on open-source tooling, so
you own your data and your scope.

## Shipped

- **Passive discovery** across many free + key-gated sources (crt.sh, CertSpotter,
  HackerTarget, AlienVault OTX, Wayback, VirusTotal, SecurityTrails, Censys,
  Shodan, …) plus local Subfinder/Amass.
- **Enrichment**: DNS resolution, HTTP(S) probing, technology fingerprinting,
  Cloudflare detection, IP grouping.
- **Subdomain takeover detection** via precise service-CNAME fingerprints
  (`can-i-take-over-xyz`) confirmed by dangling-DNS / HTTP-body signals.
- **Continuous monitoring**: scheduled scans, attack-surface change tracking
  (added / removed / went-live / IP-/tech-/port-/cert-changed), and a live
  Certificate Transparency feed (certstream).
- **Per-domain active vs. passive monitoring modes** — passive stays low-touch
  (no HTTP probing); active unlocks the loud tools.
- **Scope is law** — per-asset ownership-confidence scoring (name + owned IP
  ranges + hosting classification) gates every intrusive tool. Active scans skip
  third-party-hosted apps and shared CDN IPs.
- **Active scanning** (all opt-in, default-off, fault-isolated): nuclei
  (templates), tlsx (TLS/SSL audit), masscan→nmap (port pipeline), massdns
  (brute-force), and native cloud bucket enumeration (S3 / GCS / Azure).
- **CVE correlation** from the NVD feed for fingerprinted software.
- Web dashboard, REST API, CLI; JWT auth with admin/viewer roles; audit logging;
  Slack + email alerting; Docker-first deployment.

## In progress / next

### Phase 3 — Business context & risk prioritization
Turn raw findings into ranked risk. This is the biggest "effectiveness" lever
after scope.
- **Asset tagging**: owner, environment (prod/staging/dev), data-sensitivity,
  business unit.
- **Real risk model**: `exposure × exploitability × business-impact` rather than
  raw CVSS.
- **Threat-intel correlation**: known-exploited (KEV) / public-PoC enrichment.
- **De-duplication & noise suppression** so the queue reflects real risk.

### Phase 4 — Remediation loop & closure
Findings without closure are just noise.
- Alert routing to **Jira / PagerDuty / SIEM**, ownership assignment, ticketing.
- Finding **aging / SLA** tracking.
- **Remediation verification** — automatic re-scan to confirm a fix.

## Platform & quality (ongoing)

- **Alembic migrations** (replace the current additive schema bootstrap).
- **Task queue** (e.g. `arq`) for scan execution — durable, restart-safe,
  horizontally scalable beyond a single node.
- **Data retention / cleanup** policies for scans, findings, and audit logs.
- **Observability**: Prometheus metrics and request tracing.
- **Frontend polish**: pagination, bulk actions, deeper search/filtering,
  accessibility (ARIA / keyboard), and frontend test coverage.
- Published container images on `ghcr.io` and a `pip`-installable release.

## Later / exploratory

- GitHub / breach / secret intelligence sources.
- ASN / BGP enrichment for ownership attribution.
- Executive & trend reporting.

## Non-goals (for now)

- Becoming a general-purpose vulnerability scanner — Körüg orchestrates
  best-of-breed OSS tools rather than reinventing them.
- Requiring any paid/commercial data source as a core dependency. Optional
  paid sources may enrich results, but Körüg must be fully useful without them.

---

*Have an idea or want to contribute to a phase? Start a
[discussion](https://github.com/mfksec/korug/discussions) or open an issue.*
