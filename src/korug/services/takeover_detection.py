"""Subdomain takeover vulnerability detection service."""
import logging
import json
from typing import Optional, Dict, List
import dns.resolver
import dns.exception
import boto3

from korug.config import get_settings
from korug.services.takeover_fingerprints import match_cname, body_indicates_takeover

logger = logging.getLogger(__name__)
settings = get_settings()


class TakeoverDetector:
    """Service for detecting subdomain takeover vulnerabilities."""

    def __init__(self):
        self.confidence_threshold = settings.confidence_threshold
        self.aws_region = settings.aws_region
        self.s3_client = None
        
        # Try to initialize S3 client if AWS is configured
        try:
            self.s3_client = boto3.client("s3", region_name=self.aws_region)
        except Exception as e:
            logger.warning(f"Could not initialize S3 client: {e}")

    async def check_takeover_risks(
        self,
        subdomain: str,
        dns_records: dict,
        http_body: Optional[str] = None,
        status_code: Optional[int] = None,
    ) -> List[Dict]:
        """
        Check for subdomain takeover vulnerabilities.

        Args:
            subdomain: The subdomain to check
            dns_records: Dictionary containing DNS records (A, AAAA, CNAME, MX, NS)
            http_body: HTTP response body captured during enrichment, used for
                precise service-fingerprint matching (optional — without it the
                service check still flags NXDOMAIN-on-known-service candidates).
            status_code: HTTP status from the probe (informational).

        Returns:
            List of vulnerability findings with confidence scores
        """
        vulnerabilities = []

        # 1. Precise service takeover: CNAME points at a known service AND the
        #    target is unresolvable (NXDOMAIN) or its body matches the service's
        #    "unclaimed" fingerprint. Highest-signal check.
        service_findings = await self._check_service_takeover(subdomain, dns_records, http_body)
        vulnerabilities.extend(service_findings)

        # 2. S3 bucket takeover (authoritative bucket-existence check via boto3).
        s3_findings = await self._check_s3_takeover(subdomain, dns_records)
        vulnerabilities.extend(s3_findings)

        # 3. Generic dangling CNAME — only when the precise service check didn't
        #    already own this host, to avoid double-reporting.
        if not service_findings:
            cname_findings = await self._check_cname_orphan(subdomain, dns_records)
            vulnerabilities.extend(cname_findings)

        # 4. Orphaned MX/NS records.
        orphan_findings = await self._check_orphaned_records(subdomain, dns_records)
        vulnerabilities.extend(orphan_findings)

        return vulnerabilities

    def _is_unresolvable(self, name: str) -> bool:
        """True if ``name`` does not resolve (NXDOMAIN / no answer) — a dangling target."""
        try:
            ans = dns.resolver.resolve(name, "A", raise_on_no_answer=False)
            return ans.rrset is None
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.exception.DNSException):
            return True
        except Exception as e:  # pragma: no cover - resolver edge cases
            logger.debug("Resolve check failed for %s: %s", name, e)
            return False

    async def _check_service_takeover(
        self, subdomain: str, dns_records: dict, http_body: Optional[str]
    ) -> List[Dict]:
        """Precise takeover detection: CNAME pattern + (NXDOMAIN or body fingerprint).

        Pipeline: CNAME chain → does the target match a known service? → is the
        target dangling (NXDOMAIN) or does the response body match the service's
        fingerprint? Either signal on a known service is a takeover candidate.
        """
        cname = dns_records.get("CNAME")
        if not cname:
            return []

        candidates = match_cname(cname)
        if not candidates:
            return []

        # A dangling CNAME (target no longer resolves) is a strong, body-independent
        # signal — exactly the high-priority case from the takeover pipeline.
        nxdomain = self._is_unresolvable(cname)

        findings: List[Dict] = []
        for entry in candidates:
            body_hit = body_indicates_takeover(entry, http_body or "")
            if not (nxdomain or body_hit):
                continue

            vulnerable = entry.get("vulnerable", True)
            # NXDOMAIN on a known service, or a confirmed-vulnerable fingerprint
            # match, is critical; an edge-case service matched only by body is
            # "verify manually".
            confidence = 95.0 if (nxdomain or vulnerable is True) else 70.0
            signal = "dangling DNS (NXDOMAIN)" if nxdomain else "response fingerprint"

            findings.append({
                "vuln_type": "subdomain_takeover",
                "confidence_score": confidence,
                "details": json.dumps({
                    "category": "takeover",
                    "service": entry["service"],
                    "cname": cname,
                    "signal": signal,
                    "nxdomain": nxdomain,
                    "fingerprint_matched": body_hit,
                    "vulnerable": vulnerable,
                    "message": f"Dangling DNS → possible takeover via {entry['service']} "
                               f"({cname}) — {signal}",
                }),
            })
            logger.warning("Possible %s takeover for %s via %s (%s)",
                           entry["service"], subdomain, cname, signal)
        return findings

    async def _check_s3_takeover(self, subdomain: str, dns_records: dict) -> List[Dict]:
        """
        Check if CNAME points to an unclaimed S3 bucket.
        
        Returns list of findings with confidence scores.
        """
        findings = []
        
        if not dns_records.get("CNAME"):
            return findings
        
        cname = dns_records["CNAME"]
        
        # Check if CNAME points to S3
        if not any(s3_domain in cname for s3_domain in [
            "s3.amazonaws.com",
            "s3-",
            ".amazonaws.com",
        ]):
            return findings
        
        try:
            # Try to extract bucket name from CNAME
            # Format could be: bucket-name.s3.amazonaws.com or bucket-name.s3.region.amazonaws.com
            bucket_name = cname.split(".")[0]
            
            if not bucket_name:
                return findings
            
            # Check if bucket exists using S3 client
            if self.s3_client:
                try:
                    self.s3_client.head_bucket(Bucket=bucket_name)
                    # Bucket exists and we have access - likely not vulnerable
                    confidence = 20.0  # Low confidence in vulnerability
                    logger.info(f"S3 bucket {bucket_name} exists for {subdomain}")
                except self.s3_client.exceptions.NoSuchBucket:
                    # Bucket doesn't exist - potential takeover
                    confidence = 95.0  # High confidence
                    logger.warning(f"S3 bucket {bucket_name} not found for {subdomain}")
                except self.s3_client.exceptions.Forbidden:
                    # Bucket exists but no access - not vulnerable
                    confidence = 10.0  # Very low confidence
                    logger.info(f"S3 bucket {bucket_name} exists but access denied for {subdomain}")
                except Exception as e:
                    # Can't determine - medium confidence
                    confidence = 50.0
                    logger.debug(f"S3 check error for {bucket_name}: {e}")
            else:
                # No S3 client available - estimate based on CNAME structure
                confidence = 40.0
            
            if confidence >= self.confidence_threshold:
                findings.append({
                    "vuln_type": "s3_bucket_takeover",
                    "confidence_score": confidence,
                    "details": json.dumps({
                        "cname": cname,
                        "bucket_name": bucket_name,
                        "message": "S3 bucket referenced by CNAME does not exist or is unclaimed",
                    }),
                })
        except Exception as e:
            logger.error(f"S3 takeover check error for {subdomain}: {e}")
        
        return findings

    async def _check_cname_orphan(self, subdomain: str, dns_records: dict) -> List[Dict]:
        """
        Check for orphaned CNAME records (points to non-existent domain).
        
        Returns list of findings with confidence scores.
        """
        findings = []
        
        if not dns_records.get("CNAME"):
            return findings
        
        cname = dns_records["CNAME"]
        
        try:
            # Try to resolve the CNAME target
            dns.resolver.resolve(cname, "A", raise_on_no_answer=False)
            # If we got here, CNAME resolves - not vulnerable
            confidence = 10.0
        except (dns.resolver.NXDOMAIN, dns.exception.DNSException):
            # CNAME target doesn't exist - orphaned CNAME
            confidence = 85.0
            logger.warning(f"Orphaned CNAME {cname} detected for {subdomain}")
        except Exception as e:
            # Can't determine
            logger.debug(f"CNAME check error for {subdomain}: {e}")
            confidence = 40.0
        
        if confidence >= self.confidence_threshold:
            findings.append({
                "vuln_type": "cname_orphan",
                "confidence_score": confidence,
                "details": json.dumps({
                    "cname": cname,
                    "message": "CNAME target does not exist or is unresolvable",
                }),
            })
        
        return findings

    async def _check_orphaned_records(self, subdomain: str, dns_records: dict) -> List[Dict]:
        """
        Check for orphaned MX and NS records.
        
        Returns list of findings with confidence scores.
        """
        findings = []
        
        # Check MX records
        if dns_records.get("MX"):
            for mx_record in dns_records["MX"]:
                try:
                    dns.resolver.resolve(mx_record, "A", raise_on_no_answer=False)
                except (dns.resolver.NXDOMAIN, dns.exception.DNSException):
                    # MX target doesn't exist
                    findings.append({
                        "vuln_type": "orphaned_mx_record",
                        "confidence_score": 80.0,
                        "details": json.dumps({
                            "mx_record": mx_record,
                            "message": "MX record target does not exist",
                        }),
                    })
                    logger.warning(f"Orphaned MX record {mx_record} detected for {subdomain}")
                except Exception as e:
                    logger.debug(f"MX check error for {mx_record}: {e}")
        
        # Check NS records
        if dns_records.get("NS"):
            for ns_record in dns_records["NS"]:
                try:
                    dns.resolver.resolve(ns_record, "A", raise_on_no_answer=False)
                except (dns.resolver.NXDOMAIN, dns.exception.DNSException):
                    # NS target doesn't exist
                    findings.append({
                        "vuln_type": "orphaned_ns_record",
                        "confidence_score": 85.0,
                        "details": json.dumps({
                            "ns_record": ns_record,
                            "message": "NS record target does not exist",
                        }),
                    })
                    logger.warning(f"Orphaned NS record {ns_record} detected for {subdomain}")
                except Exception as e:
                    logger.debug(f"NS check error for {ns_record}: {e}")
        
        return findings


# Create singleton instance
takeover_detector = TakeoverDetector()
