# CLI Reference

The CLI ships with the package. Run it as `korug <command>` (after `pip install -e .`) or `python -m korug.cli <command>`. Under Docker: `docker exec korug_app python -m korug.cli <command>`.

`korug --help` lists everything; `korug <command> --help` shows options.

## Domains & scanning

```bash
korug add-domain example.com         # add a domain
korug remove-domain example.com      # remove it
korug list-domains                   # list all domains

korug scan --domain example.com      # scan one domain
korug scan                           # scan all enabled domains

korug show-results example.com       # latest subdomains + findings
korug export example.com --format xlsx   # write example.com_report.xlsx
```

## Users

```bash
korug create-user                    # interactive: username, email, password, role
korug list-users                     # list users
korug delete-user                    # remove a user
korug change-password                # set a user's password
```

Roles are `admin` and `viewer` (see [Authentication & Users](AUTH.md)).

## Setup

```bash
korug init-database                  # create database tables
korug config-slack                   # print the SLACK_WEBHOOK_URL env line to set
```

> Slack/email are normally configured from the dashboard's **Integrations** page (stored in the database). `config-slack` only helps with env-based setup.

## Scheduling

Scans run automatically via the built-in scheduler (`SCAN_SCHEDULE_HOUR`/`MINUTE`). To drive scans yourself, add a cron entry, e.g. daily at midnight:

```cron
0 0 * * * korug scan
```
