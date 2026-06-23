# CLI Reference

## Installation

The CLI tool is automatically available when you install korug:

```bash
pip install -e .
```

Or use it directly with Python:

```bash
python -m korug.cli [command]
```

## Commands

### add-domain

Add a new domain to monitor.

```bash
korug add-domain example.com
```

Output:
```
✅ Domain example.com added successfully (ID: 1)
```

### remove-domain

Remove a domain from monitoring.

```bash
korug remove-domain example.com
```

Output:
```
✅ Domain example.com removed successfully
```

### list-domains

List all monitored domains.

```bash
korug list-domains
```

Output:
```
📋 Monitored Domains:
────────────────────────────────────────────────────────────────────────────
ID    Domain                                   Status       Last Scanned
────────────────────────────────────────────────────────────────────────────
1     example.com                              ✅ Enabled   2026-06-18 12:00:00
2     test.com                                 ✅ Enabled   Never
────────────────────────────────────────────────────────────────────────────
```

### scan

Trigger a scan for domain(s).

```bash
# Scan specific domain
korug scan --domain example.com

# Scan all enabled domains
korug scan
```

Output:
```
🔍 Scanning example.com...
   Found 45 subdomains
   Found 3 vulnerabilities
✅ Scan completed
```

### show-results

Display latest scan results for a domain.

```bash
korug show-results example.com
```

Output:
```
📊 Results for example.com:
   Subdomains: 45
   Vulnerabilities: 3

⚠️  Vulnerabilities:
────────────────────────────────────────────────────────────────────────────────────────────────
Subdomain                                Type                     Confidence  False Positive
────────────────────────────────────────────────────────────────────────────────────────────────
cdn.example.com                          s3_bucket_takeover       95.0        No
mail.example.com                         cname_orphan             85.0        No
api.example.com                          orphaned_mx_record       80.0        No
────────────────────────────────────────────────────────────────────────────────────────────────
```

### export

Export scan results to file.

```bash
# Export as XLSX (currently the only format)
korug export example.com --format xlsx
```

Output:
```
✅ Export would be saved to example.com_report.xlsx
```

The XLSX file includes:
- Sheet 1: All discovered subdomains with DNS records
- Sheet 2: Vulnerabilities with details

### config-slack

Configure Slack webhook for notifications.

```bash
korug config-slack
```

Interactive prompt:
```
Slack webhook URL: https://hooks.slack.com/services/YOUR/WEBHOOK/URL
✅ Slack webhook configured
   Add to .env: SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

### init-database

Initialize the database schema.

```bash
korug init-database
```

Output:
```
✅ Database initialized successfully
```

## Global Options

All commands support these options:

```bash
# Show help
korug --help
korug [command] --help
```

## Examples

### Monitor Multiple Domains

```bash
# Add domains
korug add-domain example.com
korug add-domain test.com
korug add-domain mysite.org

# View all
korug list-domains

# Scan all at once
korug scan

# View results
korug show-results example.com
korug show-results test.com
```

### Export and Report

```bash
# Add domain
korug add-domain example.com

# Scan it
korug scan --domain example.com

# Export results
korug export example.com --format xlsx

# The file example.com_report.xlsx is ready for sharing
```

### Setup Slack Alerts

```bash
# Configure webhook
korug config-slack

# Re-edit your .env file to enable:
# SLACK_ENABLED=true

# Now scans will notify Slack
korug scan
```

### Continuous Monitoring

```bash
# Add domains to monitor
korug add-domain example.com
korug add-domain test.com

# Schedule in crontab for daily scans
# (0 0 * * * korug scan)

# Periodically check results
korug show-results example.com
```

## Troubleshooting

### Command Not Found

Ensure the package is installed:

```bash
pip install -e .
which korug
```

### Database Error

Initialize database:

```bash
korug init-database
```

### Tool Not Found (Subfinder/Amass)

Update paths in `.env`:

```bash
SUBFINDER_PATH=/usr/local/bin/subfinder
AMASS_PATH=/usr/local/bin/amass
```

## Integration with Other Tools

The CLI works well with scripting:

```bash
#!/bin/bash
# Scan all domains and export reports

for domain in $(korug list-domains | grep -oP '\b[a-z0-9]+\.[a-z]{2,}\b'); do
  korug scan --domain "$domain"
  korug export "$domain" --format xlsx
done
```
