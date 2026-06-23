"""Subdomain takeover vulnerability detection service."""
import logging
import json
from typing import Optional, Dict, List
import dns.resolver
import dns.exception
import boto3

from korug.config import get_settings

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

    async def check_takeover_risks(self, subdomain: str, dns_records: dict) -> List[Dict]:
        """
        Check for subdomain takeover vulnerabilities.
        
        Args:
            subdomain: The subdomain to check
            dns_records: Dictionary containing DNS records (A, AAAA, CNAME, MX, NS)
            
        Returns:
            List of vulnerability findings with confidence scores
        """
        vulnerabilities = []
        
        # Check for S3 bucket takeover
        s3_findings = await self._check_s3_takeover(subdomain, dns_records)
        vulnerabilities.extend(s3_findings)
        
        # Check for CNAME orphan
        cname_findings = await self._check_cname_orphan(subdomain, dns_records)
        vulnerabilities.extend(cname_findings)
        
        # Check for orphaned DNS records
        orphan_findings = await self._check_orphaned_records(subdomain, dns_records)
        vulnerabilities.extend(orphan_findings)
        
        return vulnerabilities

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
