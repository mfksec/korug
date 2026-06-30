"""Tests for the massdns subdomain brute-force service (pure helpers)."""
from korug.services.dns_bruteforce import (
    parse_massdns_simple, generate_candidates, load_words,
)


def test_parse_massdns_simple_extracts_queried_names():
    out = "\n".join([
        "www.example.com. A 93.184.216.34",
        "API.example.com. A 10.0.0.1",          # case-normalized
        "mail.example.com. CNAME ghs.google.com.",
        "trailing.example.com.",                 # too few fields -> skipped
        "",
    ])
    names = parse_massdns_simple(out)
    assert names == {"www.example.com", "api.example.com", "mail.example.com"}


def test_parse_massdns_simple_empty():
    assert parse_massdns_simple("") == set()
    assert parse_massdns_simple(None) == set()


def test_generate_candidates_builds_fqdns_deduped():
    cands = generate_candidates("Example.com", ["www", "api", "www", " mail ", ""])
    assert cands == ["www.example.com", "api.example.com", "mail.example.com"]


def test_generate_candidates_rejects_garbage_words_and_blank_domain():
    assert generate_candidates("example.com", ["bad/word", "*.wild"]) == []
    assert generate_candidates("", ["www"]) == []


def test_load_words_reads_strips_and_skips_comments(tmp_path):
    f = tmp_path / "words.txt"
    f.write_text("www\n# comment\n\n  api  \nmail\n")
    assert load_words(str(f)) == ["www", "api", "mail"]


def test_load_words_missing_file_is_empty():
    assert load_words("/nonexistent/words.txt") == []
    assert load_words("") == []
