"""Tests for the masscan->nmap port-scan pipeline (pure parsing helpers)."""
from korug.services.port_scan import parse_masscan_list, parse_nmap_xml


def test_parse_masscan_list_extracts_tcp_ports_sorted_unique():
    out = "\n".join([
        "#masscan",
        "open tcp 443 10.0.0.1 1700000000",
        "open tcp 80 10.0.0.1 1700000000",
        "open tcp 443 10.0.0.1 1700000001",  # duplicate -> collapsed
        "open udp 53 10.0.0.1 1700000000",   # udp -> ignored
        "garbage line",
        "",
    ])
    assert parse_masscan_list(out) == [80, 443]


def test_parse_masscan_list_empty():
    assert parse_masscan_list("") == []
    assert parse_masscan_list(None) == []


def test_parse_nmap_xml_reads_open_ports_and_services():
    xml = """<?xml version="1.0"?>
    <nmaprun>
      <host>
        <ports>
          <port protocol="tcp" portid="443">
            <state state="open"/>
            <service name="https" product="nginx" version="1.25.3"/>
          </port>
          <port protocol="tcp" portid="22">
            <state state="closed"/>
          </port>
          <port protocol="tcp" portid="80">
            <state state="open"/>
            <service name="http"/>
          </port>
        </ports>
      </host>
    </nmaprun>"""
    ports = parse_nmap_xml(xml)
    assert [p["port"] for p in ports] == [80, 443]   # closed port dropped, sorted
    https = next(p for p in ports if p["port"] == 443)
    assert https["service"] == "https"
    assert https["product"] == "nginx"
    assert https["version"] == "1.25.3"


def test_parse_nmap_xml_empty_or_malformed():
    assert parse_nmap_xml("") == []
    assert parse_nmap_xml("not xml") == []
