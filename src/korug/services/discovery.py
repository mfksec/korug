"""Subdomain discovery service using Subfinder, Amass, and optional external APIs."""
import json
import logging
import subprocess
from typing import Optional, Set
import aiohttp
import asyncio

from subdomain_hunter.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class DiscoveryService:
    """Service for discovering subdomains from multiple sources."""

    def __init__(self):
        self.subfinder_path = settings.subfinder_path
        self.amass_path = settings.amass_path
        self.shodan_api_key = settings.shodan_api_key
        self.urlscan_api_key = settings.urlscan_api_key

    async def discover_subdomains(self, domain: str) -> dict:
        """
        Discover subdomains using multiple sources.
        
        Args:
            domain: Domain name to scan (e.g., 'example.com')
            
        Returns:
            Dictionary with discovered subdomains and their DNS records
        """
        discovered = set()
        
        # Run Subfinder and Amass in parallel
        subfinder_results = await self._run_subfinder(domain)
        amass_results = await self._run_amass(domain)
        
        discovered.update(subfinder_results)
        discovered.update(amass_results)
        
        # Add results from external APIs if configured
        if self.shodan_api_key:
            shodan_results = await self._query_shodan(domain)
            discovered.update(shodan_results)
        
        if self.urlscan_api_key:
            urlscan_results = await self._query_urlscan(domain)
            discovered.update(urlscan_results)
        
        # Validate and resolve discovered subdomains
        resolved_subdomains = await self._resolve_subdomains(discovered, domain)
        
        logger.info(f"Discovered {len(resolved_subdomains)} subdomains for {domain}")
        
        return {
            "domain": domain,
            "total_discovered": len(resolved_subdomains),
            "subdomains": resolved_subdomains,
        }

    async def _run_subfinder(self, domain: str) -> Set[str]:
        """Run Subfinder tool."""
        results = set()
        try:
            logger.info(f"Running Subfinder for {domain}")
            result = subprocess.run(
                [self.subfinder_path, "-d", domain, "-silent"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if line.strip():
                        results.add(line.strip())
                logger.info(f"Subfinder found {len(results)} subdomains")
            else:
                logger.error(f"Subfinder error: {result.stderr}")
        except FileNotFoundError:
            logger.warning(f"Subfinder not found at {self.subfinder_path}")
        except subprocess.TimeoutExpired:
            logger.error(f"Subfinder timeout for {domain}")
        except Exception as e:
            logger.error(f"Subfinder error: {e}")
        
        return results

    async def _run_amass(self, domain: str) -> Set[str]:
        """Run Amass tool."""
        results = set()
        try:
            logger.info(f"Running Amass for {domain}")
            result = subprocess.run(
                ["amass", "enum", "-d", domain, "-norecursive"],
                capture_output=True,
                text=True,
                timeout=120,
            )
            
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if line.strip():
                        # Amass output format: [name] subdomain.example.com
                        parts = line.split()
                        if len(parts) >= 2:
                            subdomain = parts[-1]
                            if subdomain:
                                results.add(subdomain)
                logger.info(f"Amass found {len(results)} subdomains")
            else:
                logger.error(f"Amass error: {result.stderr}")
        except FileNotFoundError:
            logger.warning(f"Amass not found at {self.amass_path}")
        except subprocess.TimeoutExpired:
            logger.error(f"Amass timeout for {domain}")
        except Exception as e:
            logger.error(f"Amass error: {e}")
        
        return results

    async def _query_shodan(self, domain: str) -> Set[str]:
        """Query Shodan API for subdomains."""
        results = set()
        try:
            if not self.shodan_api_key:
                return results
            
            logger.info(f"Querying Shodan for {domain}")
            import shodan
            
            api = shodan.Shodan(self.shodan_api_key)
            hostnames = api.search(f"hostname:{domain}")
            
            for result in hostnames.get("matches", []):
                hostname = result.get("hostnames", [])
                if hostname:
                    results.update(hostname)
            
            logger.info(f"Shodan found {len(results)} subdomains")
        except Exception as e:
            logger.error(f"Shodan API error: {e}")
        
        return results

    async def _query_urlscan(self, domain: str) -> Set[str]:
        """Query urlscan.io API for subdomains."""
        results = set()
        try:
            if not self.urlscan_api_key:
                return results
            
            logger.info(f"Querying urlscan.io for {domain}")
            
            headers = {
                "API-Key": self.urlscan_api_key,
                "Content-Type": "application/json",
            }
            
            async with aiohttp.ClientSession() as session:
                # Search for URLs with this domain
                async with session.get(
                    f"https://urlscan.io/api/v1/search/?q=domain:{domain}",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for result in data.get("results", []):
                            page = result.get("page", {})
                            domain_name = page.get("domain")
                            if domain_name:
                                results.add(domain_name)
            
            logger.info(f"urlscan.io found {len(results)} subdomains")
        except Exception as e:
            logger.error(f"urlscan.io API error: {e}")
        
        return results

    async def _resolve_subdomains(self, subdomains: Set[str], domain: str) -> dict:
        """
        Resolve subdomains and get their DNS records.
        
        Args:
            subdomains: Set of discovered subdomains
            domain: Parent domain name
            
        Returns:
            Dictionary of subdomains with their DNS records
        """
        import dns.resolver
        import dns.exception
        
        resolved = {}
        
        for subdomain in subdomains:
            # Filter out entries not belonging to the target domain
            if not subdomain.endswith(domain):
                continue
            
            dns_records = {
                "A": [],
                "AAAA": [],
                "CNAME": None,
                "MX": [],
                "NS": [],
            }
            
            # Query A records
            try:
                a_answers = dns.resolver.resolve(subdomain, "A", raise_on_no_answer=False)
                dns_records["A"] = [str(rdata) for rdata in a_answers]
            except (dns.exception.DNSException, Exception):
                pass
            
            # Query AAAA records
            try:
                aaaa_answers = dns.resolver.resolve(subdomain, "AAAA", raise_on_no_answer=False)
                dns_records["AAAA"] = [str(rdata) for rdata in aaaa_answers]
            except (dns.exception.DNSException, Exception):
                pass
            
            # Query CNAME record
            try:
                cname_answers = dns.resolver.resolve(subdomain, "CNAME", raise_on_no_answer=False)
                if cname_answers:
                    dns_records["CNAME"] = str(cname_answers[0].target).rstrip(".")
            except (dns.exception.DNSException, Exception):
                pass
            
            # Query MX records
            try:
                mx_answers = dns.resolver.resolve(subdomain, "MX", raise_on_no_answer=False)
                dns_records["MX"] = [str(rdata.exchange).rstrip(".") for rdata in mx_answers]
            except (dns.exception.DNSException, Exception):
                pass
            
            # Query NS records
            try:
                ns_answers = dns.resolver.resolve(subdomain, "NS", raise_on_no_answer=False)
                dns_records["NS"] = [str(rdata.target).rstrip(".") for rdata in ns_answers]
            except (dns.exception.DNSException, Exception):
                pass
            
            # Only include subdomains that resolved to something
            if any([dns_records["A"], dns_records["AAAA"], dns_records["CNAME"], 
                   dns_records["MX"], dns_records["NS"]]):
                resolved[subdomain] = dns_records
        
        return resolved


# Create singleton instance
discovery_service = DiscoveryService()
