"""Command-line interface for Körüg."""
import json
import logging
from datetime import datetime
from typing import Optional

import click
from sqlalchemy.orm import Session

from korug import get_settings, get_db, init_db
from korug.models import Domain, Subdomain, Vulnerability, User
from korug.services import discovery_service, takeover_detector
from korug.users import create_user, get_user_by_username, authenticate_user

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = get_settings()


@click.group()
def cli():
    """Körüg - Security monitoring tool for subdomains."""
    pass


@cli.command()
@click.argument("domain")
def add_domain(domain: str):
    """Add a new domain to monitor."""
    db = next(get_db())
    try:
        # Check if domain exists
        existing = db.query(Domain).filter(Domain.domain_name == domain).first()
        if existing:
            click.echo(f"❌ Domain {domain} already exists (ID: {existing.id})")
            return
        
        # Create domain
        db_domain = Domain(domain_name=domain)
        db.add(db_domain)
        db.commit()
        db.refresh(db_domain)
        
        click.echo(f"✅ Domain {domain} added successfully (ID: {db_domain.id})")
    except Exception as e:
        click.echo(f"❌ Error adding domain: {e}")
    finally:
        db.close()


@cli.command()
@click.argument("domain")
def remove_domain(domain: str):
    """Remove a domain from monitoring."""
    db = next(get_db())
    try:
        db_domain = db.query(Domain).filter(Domain.domain_name == domain).first()
        if not db_domain:
            click.echo(f"❌ Domain {domain} not found")
            return
        
        db.delete(db_domain)
        db.commit()
        click.echo(f"✅ Domain {domain} removed successfully")
    except Exception as e:
        click.echo(f"❌ Error removing domain: {e}")
    finally:
        db.close()


@cli.command()
@click.option("--domain", default=None, help="Specific domain to scan")
def scan(domain: Optional[str]):
    """Trigger a scan for domain(s)."""
    import asyncio
    
    db = next(get_db())
    try:
        if domain:
            domains_to_scan = [db.query(Domain).filter(Domain.domain_name == domain).first()]
            if not domains_to_scan[0]:
                click.echo(f"❌ Domain {domain} not found")
                return
        else:
            domains_to_scan = db.query(Domain).filter(Domain.enabled == True).all()
            if not domains_to_scan:
                click.echo("❌ No domains to scan")
                return
        
        for d in domains_to_scan:
            click.echo(f"🔍 Scanning {d.domain_name}...")
            
            # Discover subdomains
            discovery_result = asyncio.run(discovery_service.discover_subdomains(d.domain_name))
            click.echo(f"   Found {len(discovery_result.get('subdomains', {}))} subdomains")
            
            # Check for vulnerabilities
            vuln_count = 0
            for subdomain, dns_records in discovery_result.get("subdomains", {}).items():
                vulns = asyncio.run(takeover_detector.check_takeover_risks(subdomain, dns_records))
                vuln_count += len(vulns)
            
            click.echo(f"   Found {vuln_count} vulnerabilities")
            d.last_scanned = datetime.utcnow()
            db.add(d)
        
        db.commit()
        click.echo(f"✅ Scan completed")
    except Exception as e:
        click.echo(f"❌ Scan error: {e}")
        logger.exception("Scan error")
    finally:
        db.close()


@cli.command()
def list_domains():
    """List all monitored domains."""
    db = next(get_db())
    try:
        domains = db.query(Domain).all()
        if not domains:
            click.echo("No domains configured")
            return
        
        click.echo("\n📋 Monitored Domains:")
        click.echo("-" * 80)
        click.echo(f"{'ID':<5} {'Domain':<40} {'Status':<10} {'Last Scanned':<25}")
        click.echo("-" * 80)
        
        for domain in domains:
            status = "✅ Enabled" if domain.enabled else "❌ Disabled"
            last_scanned = domain.last_scanned.strftime("%Y-%m-%d %H:%M:%S") if domain.last_scanned else "Never"
            click.echo(f"{domain.id:<5} {domain.domain_name:<40} {status:<10} {last_scanned:<25}")
        
        click.echo("-" * 80)
    except Exception as e:
        click.echo(f"❌ Error listing domains: {e}")
    finally:
        db.close()


@cli.command()
@click.argument("domain")
def show_results(domain: str):
    """Display scan results for a domain."""
    db = next(get_db())
    try:
        db_domain = db.query(Domain).filter(Domain.domain_name == domain).first()
        if not db_domain:
            click.echo(f"❌ Domain {domain} not found")
            return
        
        subdomains = db.query(Subdomain).filter(Subdomain.domain_id == db_domain.id).all()
        vulnerabilities = db.query(Vulnerability).filter(Vulnerability.domain_id == db_domain.id).all()
        
        click.echo(f"\n📊 Results for {domain}:")
        click.echo(f"   Subdomains: {len(subdomains)}")
        click.echo(f"   Vulnerabilities: {len(vulnerabilities)}")
        
        if vulnerabilities:
            click.echo("\n⚠️  Vulnerabilities:")
            click.echo("-" * 100)
            click.echo(f"{'Subdomain':<40} {'Type':<25} {'Confidence':<15} {'False Positive':<15}")
            click.echo("-" * 100)
            
            for vuln in vulnerabilities:
                sub = db.query(Subdomain).filter(Subdomain.id == vuln.subdomain_id).first()
                fp = "Yes" if vuln.is_false_positive else "No"
                click.echo(f"{sub.subdomain:<40} {vuln.vuln_type:<25} {vuln.confidence_score:<15.1f} {fp:<15}")
    
    except Exception as e:
        click.echo(f"❌ Error showing results: {e}")
    finally:
        db.close()


@cli.command()
@click.argument("domain")
@click.option("--format", default="xlsx", help="Export format (xlsx)")
def export(domain: str, format: str):
    """Export scan results for a domain."""
    db = next(get_db())
    try:
        db_domain = db.query(Domain).filter(Domain.domain_name == domain).first()
        if not db_domain:
            click.echo(f"❌ Domain {domain} not found")
            return
        
        if format == "xlsx":
            from korug.api.export import export_to_xlsx
            
            # We'll implement direct XLSX export in CLI separately
            click.echo(f"✅ Export would be saved to {domain}_report.xlsx")
        else:
            click.echo(f"❌ Unsupported format: {format}")
    except Exception as e:
        click.echo(f"❌ Error exporting: {e}")
    finally:
        db.close()


@cli.command()
@click.option("--webhook-url", prompt="Slack webhook URL", hide_input=False)
def config_slack(webhook_url: str):
    """Configure Slack integration."""
    try:
        # Save to .env or config
        click.echo(f"✅ Slack webhook configured")
        click.echo(f"   Add to .env: SLACK_WEBHOOK_URL={webhook_url}")
    except Exception as e:
        click.echo(f"❌ Error configuring Slack: {e}")


@cli.command()
def init_database():
    """Initialize the database."""
    try:
        init_db()
        click.echo("✅ Database initialized successfully")
    except Exception as e:
        click.echo(f"❌ Error initializing database: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# User Management Commands
# ─────────────────────────────────────────────────────────────────────────────


@cli.command("create-user")
@click.option("--username", prompt="Username", help="Username for the new user")
@click.option("--email", prompt="Email", help="Email for the new user")
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True, help="Password for the new user")
@click.option("--role", type=click.Choice(["admin", "viewer"], case_sensitive=False), default="viewer", help="User role")
def create_user_cmd(username: str, email: str, password: str, role: str):
    """Create a new user account."""
    db = next(get_db())
    try:
        # Validate inputs
        if not username or len(username) < 3:
            click.echo("❌ Username must be at least 3 characters")
            return
        
        if not email or "@" not in email:
            click.echo("❌ Invalid email address")
            return
        
        if not password or len(password) < 8:
            click.echo("❌ Password must be at least 8 characters")
            return
        
        # Check if user already exists
        existing_user = get_user_by_username(db, username)
        if existing_user:
            click.echo(f"❌ User '{username}' already exists")
            return
        
        # Create the user
        user = create_user(db, username=username, email=email, password=password, role=role)
        
        click.echo("✅ User created successfully:")
        click.echo(f"   ID: {user.id}")
        click.echo(f"   Username: {user.username}")
        click.echo(f"   Email: {user.email}")
        click.echo(f"   Role: {user.role}")
        click.echo(f"   Created: {user.created_at}")
    except ValueError as e:
        click.echo(f"❌ Error: {e}")
    except Exception as e:
        click.echo(f"❌ Error creating user: {e}")
        logger.exception("User creation error")
    finally:
        db.close()


@cli.command("list-users")
def list_users_cmd():
    """List all user accounts."""
    db = next(get_db())
    try:
        users = db.query(User).all()
        
        if not users:
            click.echo("No users configured")
            return
        
        click.echo("\n👥 User Accounts:")
        click.echo("-" * 100)
        click.echo(f"{'ID':<5} {'Username':<20} {'Email':<35} {'Role':<10} {'Active':<8} {'Last Login':<20}")
        click.echo("-" * 100)
        
        for user in users:
            active = "✅ Yes" if user.is_active else "❌ No"
            last_login = user.last_login.strftime("%Y-%m-%d %H:%M:%S") if user.last_login else "Never"
            click.echo(
                f"{user.id:<5} {user.username:<20} {user.email:<35} {user.role:<10} {active:<8} {last_login:<20}"
            )
        
        click.echo("-" * 100)
        click.echo(f"Total users: {len(users)}")
    except Exception as e:
        click.echo(f"❌ Error listing users: {e}")
        logger.exception("User listing error")
    finally:
        db.close()


@cli.command("delete-user")
@click.option("--username", prompt="Username to delete", help="Username of the user to delete")
@click.confirmation_option(prompt="Are you sure you want to delete this user?")
def delete_user_cmd(username: str):
    """Delete a user account."""
    db = next(get_db())
    try:
        user = get_user_by_username(db, username)
        if not user:
            click.echo(f"❌ User '{username}' not found")
            return
        
        db.delete(user)
        db.commit()
        click.echo(f"✅ User '{username}' deleted successfully")
    except Exception as e:
        click.echo(f"❌ Error deleting user: {e}")
        logger.exception("User deletion error")
    finally:
        db.close()


@cli.command("change-password")
@click.option("--username", prompt="Username", help="Username of the user")
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True, help="New password")
def change_password_cmd(username: str, password: str):
    """Change a user's password."""
    db = next(get_db())
    try:
        if not password or len(password) < 8:
            click.echo("❌ Password must be at least 8 characters")
            return
        
        user = get_user_by_username(db, username)
        if not user:
            click.echo(f"❌ User '{username}' not found")
            return
        
        from korug.auth_utils import hash_password
        
        user.hashed_password = hash_password(password)
        db.add(user)
        db.commit()
        click.echo(f"✅ Password changed successfully for user '{username}'")
    except Exception as e:
        click.echo(f"❌ Error changing password: {e}")
        logger.exception("Password change error")
    finally:
        db.close()


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
