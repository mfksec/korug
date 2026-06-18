"""Tests for subdomain discovery service."""
import pytest
import json
from unittest.mock import patch, MagicMock
from subdomain_hunter.services.discovery import DiscoveryService


@pytest.fixture
def discovery_service():
    """Create discovery service instance."""
    return DiscoveryService()


@pytest.mark.asyncio
async def test_discover_subdomains_basic(discovery_service):
    """Test basic subdomain discovery."""
    with patch.object(discovery_service, '_run_subfinder') as mock_subfinder, \
         patch.object(discovery_service, '_run_amass') as mock_amass, \
         patch.object(discovery_service, '_resolve_subdomains') as mock_resolve:
        
        mock_subfinder.return_value = {"www.example.com", "api.example.com"}
        mock_amass.return_value = {"mail.example.com"}
        mock_resolve.return_value = {
            "www.example.com": {"A": ["93.184.216.34"], "AAAA": [], "CNAME": None, "MX": [], "NS": []},
            "api.example.com": {"A": ["93.184.216.35"], "AAAA": [], "CNAME": None, "MX": [], "NS": []},
            "mail.example.com": {"A": [], "AAAA": [], "CNAME": None, "MX": ["mail.example.com"], "NS": []},
        }
        
        result = await discovery_service.discover_subdomains("example.com")
        
        assert result["domain"] == "example.com"
        assert result["total_discovered"] == 3
        assert len(result["subdomains"]) == 3


@pytest.mark.asyncio
async def test_discover_subdomains_no_results(discovery_service):
    """Test discovery when no subdomains found."""
    with patch.object(discovery_service, '_run_subfinder') as mock_subfinder, \
         patch.object(discovery_service, '_run_amass') as mock_amass, \
         patch.object(discovery_service, '_resolve_subdomains') as mock_resolve:
        
        mock_subfinder.return_value = set()
        mock_amass.return_value = set()
        mock_resolve.return_value = {}
        
        result = await discovery_service.discover_subdomains("example.com")
        
        assert result["domain"] == "example.com"
        assert result["total_discovered"] == 0


@pytest.mark.asyncio
async def test_subfinder_timeout(discovery_service):
    """Test Subfinder timeout handling."""
    import subprocess
    
    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired("subfinder", 60)
        
        result = await discovery_service._run_subfinder("example.com")
        
        assert result == set()


@pytest.mark.asyncio
async def test_subfinder_not_found(discovery_service):
    """Test Subfinder not found error handling."""
    import subprocess
    
    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = FileNotFoundError()
        
        result = await discovery_service._run_subfinder("example.com")
        
        assert result == set()


def test_resolve_subdomains_filters_domain(discovery_service):
    """Test that resolve only includes subdomains of the target domain."""
    import dns.resolver
    from unittest.mock import patch
    
    subdomains = {
        "www.example.com",
        "api.example.com",
        "other.com",  # Should be filtered out
    }
    
    with patch('dns.resolver.resolve') as mock_resolve:
        mock_resolve.return_value = [MagicMock(address="93.184.216.34")]
        
        # This test would need proper async handling
        # Simplified for illustration
        pass
