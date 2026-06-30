<h1 align="center">𐰚𐰘𐰺𐰈𐰏 Körüg</h1>

<p align="center">
    <b>Self-hosted External Attack Surface Management.</b><br/>
    Continuously discover, monitor, and secure everything your organization exposes to the internet — open-source, scope-aware, and built on best-of-breed tooling. Own your data.
</p>

<p align="center">
    <img src="https://img.shields.io/badge/python-3.11%2B-blue?style=flat-square" alt="Python 3.11+" />
    <a href="LICENSE"><img src="https://img.shields.io/github/license/mfksec/korug?style=flat-square" alt="License: Apache-2.0" /></a>
    <a href="https://github.com/mfksec/korug/releases"><img src="https://img.shields.io/github/v/release/mfksec/korug?style=flat-square&include_prereleases" alt="Release" /></a>
</p>

# Overview

Körüg (Old Turkic for "protection/guardian") is a self-hosted EASM platform: it continuously **discovers** your internet-facing assets, **attributes** ownership, **enriches** and **assesses** them, and **alerts** when your attack surface changes or a risk appears — through a web dashboard, REST API, and CLI.

It unifies the best open-source recon and scanning tools (subfinder, nuclei, tlsx, masscan, massdns, Amass, and more) behind one continuous, **scope-aware** control plane — so instead of running one-off CLI scans, you get an always-on inventory with change tracking, takeover detection, and prioritized findings. **"Scope is law"**: intrusive tools only ever run against assets you've proven you own.

All dashboards reflect real scan data: charts, alerts, and statistics are computed from your own scans, not seeded samples.

<!-- TODO(launch): replace this static screenshot with a ~60s animated demo GIF (clone → docker compose up → add a domain → findings populate → Slack alert). Demo media is the single biggest driver of conversion for security OSS. -->
<p align="center">
    <img src="docs/images/dashboard.png" alt="Körüg dashboard — stat cards, findings timeline, risk distribution, latest vulnerabilities and recent alerts" width="900" />
</p>

## Why Körüg?

Körüg's differentiators: **scope-is-law ownership gating** before any intrusive probe, **passive/active monitoring modes** per domain, and a **continuous loop** (discover → attribute → enrich → assess → prioritize → alert → verify) rather than a one-time scan. See the [roadmap](ROADMAP.md) for where it's headed.

# Features

- **Passive discovery**
- **Enrichment & detection**
- **Continuous attack-surface monitoring**
- **Dashboard**
- **Alerts & notifications**
- **Access control & administration**
- **Automation & reporting**

# Installation

```bash
git clone https://github.com/mfksec/korug.git
cd korug
cp docker/.env.docker docker/.env   # Docker config; set JWT_SECRET_KEY, API_KEY, DB credentials
docker compose -f docker/docker-compose.yml up -d --build
```

> Use `--build` (and `--build` again when updating) so Docker doesn't reuse a stale cached image.

Dashboard: http://localhost:3000 | API docs: http://localhost:8000/docs

On first run an initial `admin` account is created. If `ADMIN_PASSWORD` is not set, a strong random password is generated and printed to the logs once — capture it and change it after logging in.

> Configure secrets via environment variables, never in committed files. See [.env.example](.env.example) for all options. Slack notifications are configured at runtime from the dashboard's **Settings → Integrations** tab.

# Acknowledgements

Körüg builds on the work of the open-source security community. Thanks to:

- **[can-i-take-over-xyz](https://github.com/EdOverflow/can-i-take-over-xyz)** by EdOverflow and contributors — the source of the subdomain-takeover service CNAME patterns and fingerprints used in [`takeover_fingerprints.py`](src/korug/services/takeover_fingerprints.py). Licensed **CC BY-SA 4.0**; our curated subset is a derivative work shared under the same terms.
- **Discovery & recon tooling/data**: [ProjectDiscovery](https://github.com/projectdiscovery) (subfinder, [nuclei](https://github.com/projectdiscovery/nuclei), [tlsx](https://github.com/projectdiscovery/tlsx)), [OWASP Amass](https://github.com/owasp-amass/amass), [massdns](https://github.com/blechschmidt/massdns) (Quirin Scheitle / blechschmidt), [masscan](https://github.com/robertdavidgraham/masscan) (Robert Graham) and [nmap](https://nmap.org), [crt.sh](https://crt.sh) and CertSpotter (Certificate Transparency), HackerTarget, RapidDNS, AlienVault OTX, ThreatMiner, the Wayback Machine, and the optional providers VirusTotal, SecurityTrails, BinaryEdge, Censys, urlscan.io, and Shodan.
- **Cloud bucket enumeration**: the permutation approach is inspired by [cloud_enum](https://github.com/initstring/cloud_enum) (initstring) and [S3Scanner](https://github.com/sa7mon/S3Scanner) (sa7mon).
- **Vulnerability data**: the [NVD](https://nvd.nist.gov/) CVE feed (NIST).
- **Core libraries**: FastAPI, SQLAlchemy, dnspython, aiohttp, boto3, nmap + defusedxml, APScheduler, React, Vite, MUI, and Recharts.

Trademarks and project names belong to their respective owners; listing here does not imply endorsement.

# Documentation

- [Quick Start](docs/QUICKSTART.md)
- [User Guide](docs/USER_GUIDE.md)
- [API Reference](docs/API.md)
- [CLI Reference](docs/CLI.md)
- [Authentication](docs/AUTH.md)
- [Architecture](docs/ARCHITECTURE.md)

<p align="center">
    <a href="LICENSE">
        <img src="https://img.shields.io/github/license/mfksec/korug?style=flat-square" />
    </a>
    <a href="https://github.com/mfksec/korug">
        <img src="https://img.shields.io/github/stars/mfksec/korug?style=social" />
    </a>
</p>
