"""Tests for the attack-surface change-detection service."""
from korug.models import Domain, Subdomain, AssetChange, Alert
from korug.services.changes import diff_subdomain, record_changes


# ---- diff_subdomain (pure) -----------------------------------------------

def test_diff_returns_empty_for_first_observation():
    assert diff_subdomain(None, {"is_alive": True, "resolved_ips": ["1.2.3.4"]}) == []


def test_diff_detects_went_live_and_offline():
    prior = {"is_alive": False, "status_code": None, "resolved_ips": [], "technologies": [], "open_ports": []}
    current = {"is_alive": True, "status_code": 200, "resolved_ips": [], "technologies": [], "open_ports": []}
    types = [c["change_type"] for c in diff_subdomain(prior, current)]
    assert "went_live" in types
    # reverse direction
    types_back = [c["change_type"] for c in diff_subdomain(current, prior)]
    assert "went_offline" in types_back


def test_diff_detects_ip_tech_and_port_changes():
    prior = {"is_alive": True, "resolved_ips": ["1.1.1.1"], "technologies": ["nginx"], "open_ports": [{"port": 80}]}
    current = {"is_alive": True, "resolved_ips": ["2.2.2.2"], "technologies": ["nginx", "PHP"], "open_ports": [{"port": 80}, {"port": 443}]}
    types = {c["change_type"] for c in diff_subdomain(prior, current)}
    assert {"ip_changed", "tech_changed", "ports_changed"} <= types


def test_diff_no_changes_when_identical():
    state = {"is_alive": True, "status_code": 200, "resolved_ips": ["1.1.1.1"], "technologies": ["nginx"], "open_ports": [{"port": 443}]}
    assert diff_subdomain(state, dict(state)) == []


def test_diff_handles_port_dicts_and_scalars():
    # open_ports may be dicts (from enrichment) or bare ints (older rows).
    prior = {"is_alive": True, "resolved_ips": [], "technologies": [], "open_ports": [80]}
    current = {"is_alive": True, "resolved_ips": [], "technologies": [], "open_ports": [{"port": 80}]}
    assert diff_subdomain(prior, current) == []  # 80 == 80, no change


# ---- record_changes (persistence + alerting) -----------------------------

def _seed(db):
    domain = Domain(domain_name="example.com")
    db.add(domain)
    db.commit()
    db.refresh(domain)
    sub = Subdomain(domain_id=domain.id, subdomain="www.example.com")
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return domain, sub


def test_record_changes_persists_rows_and_alerts(db_session):
    domain, sub = _seed(db_session)
    n = record_changes(
        db_session, domain_id=domain.id, subdomain_id=sub.id, scan_id=None,
        target=sub.subdomain,
        changes=[
            {"change_type": "subdomain_added", "old_value": None, "new_value": "1.2.3.4"},
            {"change_type": "tech_changed", "old_value": "nginx", "new_value": "nginx, PHP"},
        ],
    )
    db_session.commit()
    assert n == 2
    assert db_session.query(AssetChange).count() == 2
    # subdomain_added alerts; tech_changed does not.
    alerts = db_session.query(Alert).all()
    assert len(alerts) == 1
    assert alerts[0].alert_type == "change:subdomain_added"


def test_record_changes_can_suppress_alerts(db_session):
    domain, sub = _seed(db_session)
    record_changes(
        db_session, domain_id=domain.id, subdomain_id=sub.id, scan_id=None,
        target=sub.subdomain,
        changes=[{"change_type": "went_live", "old_value": None, "new_value": "200"}],
        raise_alerts=False,
    )
    db_session.commit()
    assert db_session.query(AssetChange).count() == 1
    assert db_session.query(Alert).count() == 0
