"""Tests for cloud bucket enumeration (pure helpers)."""
from korug.services.bucket_enum import (
    keyword_from_domain, generate_bucket_names, azure_account,
    candidate_urls, classify_response,
)


def test_keyword_from_domain():
    assert keyword_from_domain("example.com") == "example"
    assert keyword_from_domain("sub.example.com") == "example"
    assert keyword_from_domain("example.co.uk") == "example"
    assert keyword_from_domain("EXAMPLE.IO") == "example"
    assert keyword_from_domain("") == ""


def test_generate_bucket_names_includes_keyword_and_affix_permutations():
    names = generate_bucket_names("example")
    assert "example" in names
    assert "example-backups" in names
    assert "prod-example" in names
    assert "examplestatic" in names           # no-separator concatenation
    assert len(names) == len(set(names))        # deduped
    assert len(names) <= 150                    # bounded


def test_generate_bucket_names_empty_keyword():
    assert generate_bucket_names("") == []
    assert generate_bucket_names("!!!") == []


def test_azure_account_normalizes_and_validates_length():
    assert azure_account("example-prod") == "exampleprod"   # separators stripped
    assert azure_account("ab") is None                       # too short (<3)
    assert azure_account("a" * 30) is None                   # too long (>24)


def test_candidate_urls_covers_providers():
    probes = candidate_urls("example-dev")
    providers = {p["provider"] for p in probes}
    assert providers == {"s3", "gcs", "azure"}
    s3 = next(p for p in probes if p["provider"] == "s3")
    assert s3["url"] == "https://example-dev.s3.amazonaws.com/"
    azure = next(p for p in probes if p["provider"] == "azure")
    assert "exampledev.blob.core.windows.net" in azure["url"]   # dashes stripped for azure


def test_candidate_urls_skips_azure_when_name_invalid():
    # A name that can't form a valid azure account (too short after stripping).
    probes = candidate_urls("ab")
    assert {p["provider"] for p in probes} == {"s3", "gcs"}


def test_classify_response_s3():
    assert classify_response("s3", 200, "<ListBucketResult>") == {"exists": True, "public": True}
    assert classify_response("s3", 403, "AccessDenied") == {"exists": True, "public": False}
    assert classify_response("s3", 404, "NoSuchBucket") == {"exists": False, "public": False}


def test_classify_response_azure_requires_listing_marker():
    assert classify_response("azure", 200, "<EnumerationResults>")["public"] is True
    assert classify_response("azure", 200, "something else")["public"] is False
    assert classify_response("azure", 409, "")["exists"] is True
