# User Guide: Körüg Web Dashboard

Welcome to Körüg! This guide will help you get the most out of the web dashboard interface.

## 📋 Table of Contents

1. [Getting Started](#getting-started)
2. [Dashboard Overview](#dashboard-overview)
3. [Managing Domains](#managing-domains)
4. [Running Scans](#running-scans)
5. [Viewing Results](#viewing-results)
6. [Understanding Vulnerabilities](#understanding-vulnerabilities)
7. [Settings & Configuration](#settings--configuration)
8. [Tips & Tricks](#tips--tricks)

---

## Getting Started

### First Login

1. **Open the Dashboard**: Navigate to `http://localhost:3000` (Docker) or `http://localhost:5174` (Development)

2. **Login Credentials** (default):
   - Username: `admin`
   - Password: `admin123`

3. **⚠️ IMPORTANT: Change Your Password**
   - Go to **Settings** (⚙️ icon in top-right)
   - Click **Account Settings**
   - Change your password immediately

### Generating an API Key

For programmatic access (CLI, scripts, third-party apps):

1. Go to **Settings** (⚙️ icon)
2. Click **API Keys** tab
3. Click **Generate New Key**
4. **Copy and save the key** - It won't be shown again!
5. Use it in API calls: `Authorization: Bearer YOUR_API_KEY`

---

## Dashboard Overview

The main dashboard provides a high-level summary of your monitoring:

### Dashboard Tabs

| Tab | Purpose |
|-----|---------|
| **Dashboard** | Overview, charts, recent alerts |
| **Domains** | Add, manage, and view all domains |
| **Vulnerabilities** | View and manage detected issues |
| **Alerts** | History of Slack notifications |
| **Audit Logs** | Security event tracking |
| **Settings** | Configuration and preferences |

### Key Metrics

- **Total Domains**: Number of domains being monitored
- **Active Subdomains**: Count of discovered subdomains
- **Vulnerabilities Found**: Total security issues detected
- **False Positives**: Issues marked as non-critical
- **Last Scan**: When the most recent scan completed

---

## Managing Domains

### Adding a Domain

1. Click the **Domains** tab
2. Click **➕ Add Domain** button
3. Enter the domain name (e.g., `example.com`)
4. Click **Add**
5. The domain will appear in the list immediately

### Viewing Domain Details

1. Click on a domain in the list
2. You'll see:
   - **Subdomains**: All discovered subdomains with DNS records
   - **DNS Records**: A/AAAA/CNAME/MX/NS information
   - **Vulnerabilities**: Issues found for this domain
   - **Scan History**: Previous scan results

### Filtering & Searching

- **Search Box**: Find domains by name (top of list)
- **Filter Options**:
  - By vulnerability count
  - By last scan date
  - By status (active/archived)

### Removing a Domain

1. Click the **⋮ (three dots)** menu on the domain
2. Click **Delete**
3. Confirm deletion

---

## Running Scans

### Manual Scan

1. Go to **Domains** tab
2. Click on a domain to select it
3. Click **🔍 Start Scan** button
4. Wait for scan to complete (1-5 minutes depending on domain)
5. Results appear automatically

### Scheduled Scans

1. Go to **Settings** (⚙️ icon)
2. Click **Scanning Configuration**
3. Set:
   - **Schedule Time**: When to run daily scans (e.g., 12:00 AM UTC)
   - **Confidence Threshold**: Minimum 75% (only alert on high-confidence findings)
4. Click **Save**

Scans will run automatically at the configured time for all monitored domains.

### Scan Status

- 🟢 **Completed**: Scan finished successfully
- 🟡 **In Progress**: Currently scanning
- 🔴 **Failed**: Scan encountered an error
- ⚪ **Scheduled**: Waiting for scheduled time

---

## Viewing Results

### Subdomain List

Shows all discovered subdomains for a domain:

| Column | Meaning |
|--------|---------|
| **Subdomain** | The discovered subdomain name |
| **DNS A Record** | IPv4 address (if exists) |
| **DNS CNAME** | Canonical name (if exists) |
| **First Seen** | When subdomain was first discovered |
| **Last Seen** | Most recent discovery time |

### DNS Records

For each subdomain, view:
- **A Records**: IPv4 addresses
- **AAAA Records**: IPv6 addresses
- **CNAME**: Alias targets
- **MX Records**: Mail server targets
- **NS Records**: Nameserver targets

### Vulnerability Details

When you click on a vulnerability, see:
- **Type**: S3 Takeover, CNAME Orphan, or DNS Orphan
- **Severity**: How dangerous the issue is
- **Confidence**: How certain the detection is (75-95%)
- **Description**: Explanation of the vulnerability
- **Recommendation**: How to fix it
- **Evidence**: Technical details used for detection

---

## Understanding Vulnerabilities

### Types of Vulnerabilities

#### 🔴 S3 Bucket Takeover (95% Confidence)
- **What**: A CNAME points to an unclaimed S3 bucket
- **Risk**: Attacker can claim the bucket and serve malicious content
- **Fix**: Update CNAME or claim the S3 bucket
- **Example**: `cdn.example.com CNAME d1234567890.cloudfront.net` → Unclaimed S3 bucket

#### 🟠 CNAME Orphan (85% Confidence)
- **What**: A CNAME record points to a target that doesn't exist
- **Risk**: Potential subdomain takeover if attacker claims the target
- **Fix**: Remove the CNAME record or update it to a valid target
- **Example**: `blog.example.com CNAME nonexistent-blog.example.com` → Target doesn't exist

#### 🟡 DNS Orphan (80-85% Confidence)
- **What**: MX or NS records point to targets that don't exist
- **Risk**: Mail delivery issues, potential for hijacking
- **Fix**: Update or remove the orphaned records
- **Example**: `example.com MX oldmail.example.com` → Target no longer exists

### Severity Levels

| Level | Color | Meaning |
|-------|-------|---------|
| **Critical** | 🔴 Red | Immediate takeover risk, fix immediately |
| **High** | 🟠 Orange | Significant security risk, fix soon |
| **Medium** | 🟡 Yellow | Potential issue, monitor and fix when possible |
| **Low** | 🟢 Green | Minimal risk, informational |

### Marking False Positives

If a vulnerability is actually safe (e.g., you intentionally have an orphaned CNAME):

1. Click on the vulnerability
2. Click **Mark as False Positive**
3. Enter a reason (optional)
4. Click **Confirm**

False positives won't trigger alerts in the future.

---

## Settings & Configuration

### Account Settings

1. Go to **Settings** (⚙️ icon)
2. Click **Account** tab
3. Update:
   - **Email**: Your contact email
   - **Full Name**: Your name
   - **Password**: Change your login password
4. Click **Save Changes**

### API Keys

**Generate API Key** (for programmatic access):
1. Click **Settings** → **API Keys**
2. Click **Generate New Key**
3. Copy the key immediately
4. Use in requests:
   ```bash
   curl -H "Authorization: Bearer YOUR_API_KEY" http://localhost:8000/api/domains/
   ```

**Revoke API Key**:
1. Click **Settings** → **API Keys**
2. Click **Revoke** next to the key
3. Any scripts using that key will stop working

### Slack Integration (Optional)

To get real-time Slack alerts:

1. Create a Slack webhook:
   - Go to your Slack workspace settings
   - Create an Incoming Webhook
   - Copy the webhook URL

2. In Körüg:
   - Go to **Settings** (⚙️ icon)
   - Click **Integrations** tab
   - Paste the webhook URL
   - Click **Test Connection**
   - Click **Enable**

3. Now receive notifications when vulnerabilities are found!

### Scanning Configuration

1. Go to **Settings** (⚙️ icon)
2. Click **Scanning** tab
3. Configure:
   - **Enable Scheduled Scans**: Turn on/off automatic scanning
   - **Scan Time**: When to run daily (default: 00:00 UTC)
   - **Confidence Threshold**: Minimum confidence to alert (75-100%)
4. Click **Save**

### External APIs (Optional)

For enhanced discovery capabilities:

1. Go to **Settings** → **External APIs**
2. Add your API keys:
   - **Shodan.io**: For IP and port information
   - **urlscan.io**: For URL archive data
3. Click **Save**

---

## Tips & Tricks

### 🎯 Best Practices

1. **Start Small**: Add one domain and run a scan to get familiar
2. **Set Threshold**: Set confidence to 85%+ to avoid false positives
3. **Schedule Scans**: Use scheduled scans for continuous monitoring
4. **Review Regularly**: Check vulnerabilities weekly
5. **Export Data**: Use the export feature for reports
6. **Mark False Positives**: Keep your results clean and actionable

### ⚡ Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl/Cmd + K` | Quick search for domains |
| `Ctrl/Cmd + ?` | Show keyboard shortcuts |
| `G` then `D` | Go to Domains tab |
| `G` then `V` | Go to Vulnerabilities tab |
| `G` then `A` | Go to Alerts tab |

### 📊 Export & Reports

1. Click **Export** button on any tab
2. Choose format:
   - **CSV**: For spreadsheets
   - **JSON**: For programmatic processing
   - **XLSX**: For formatted reports
3. File downloads automatically

### 🔍 Advanced Filtering

**On Vulnerabilities Tab:**
- Filter by type (S3, CNAME, DNS)
- Filter by severity (Critical, High, Medium, Low)
- Filter by status (Open, Resolved, False Positive)
- Sort by date or confidence

### 💡 Workflow Example

```
1. Monday: Add 5 domains to monitor
   └─ Go to Domains → Add each domain

2. Tuesday: Run first scans manually
   └─ Click each domain → Start Scan

3. Wednesday: Review vulnerabilities
   └─ Go to Vulnerabilities → Triage issues
   └─ Mark false positives

4. Thursday: Set up Slack alerts
   └─ Settings → Integrations → Add Slack webhook
   └─ Enable Slack notifications

5. Friday: Schedule daily scans
   └─ Settings → Scanning → Set schedule time
   └─ Future scans run automatically
```

---

## Troubleshooting

### 🚨 Common Issues

**Issue**: "Cannot connect to API"
- **Solution**: Ensure backend is running (Port 8000)
- Backend logs: `docker logs korug_app`

**Issue**: "Scan not finding subdomains"
- **Solution**: Check if discovery tools are installed
- Ensure Shodan/urlscan API keys are configured (Settings)

**Issue**: "Too many false positives"
- **Solution**: Increase Confidence Threshold in Settings
- Mark known false positives as "False Positive"

**Issue**: "Forgot admin password"
- **Solution**: Reset database in Settings → Advanced
- Or restart containers: `docker-compose restart`

---

## Getting Help

- 📖 [Full Documentation](https://github.com/mfksec/korug/docs/)
- 🐛 [Report Issues](https://github.com/mfksec/korug/issues)
- 💬 [Discussions](https://github.com/mfksec/korug/discussions)
- 🔒 [Security Issues](SECURITY.md)

---

**Happy monitoring! 🛡️**
