"""Tests for Graph API client."""

import pytest
from unittest.mock import Mock, patch
from outlook_ai.graph import OutlookGraphClient


class TestOutlookGraphClient:
    """Test Graph API client."""

    def test_escape_odata_string(self):
        """Test OData string escaping."""
        client = OutlookGraphClient(client_id="test")
        
        # Test single quote escaping
        assert client._escape_odata_string("test") == "test"
        assert client._escape_odata_string("test'quote") == "test''quote"
        assert client._escape_odata_string("it's a test") == "it''s a test"

    def test_validate_folder_valid(self):
        """Test folder validation with valid names."""
        client = OutlookGraphClient(client_id="test")
        
        # Valid folder names
        assert client._validate_folder("INBOX") == "INBOX"
        assert client._validate_folder("Sent") == "Sent"
        assert client._validate_folder("自定义文件夹") == "自定义文件夹"

    def test_validate_folder_path_traversal(self):
        """Test folder validation blocks path traversal."""
        client = OutlookGraphClient(client_id="test")
        
        # Invalid folder names
        with pytest.raises(ValueError):
            client._validate_folder("../etc/passwd")
        
        with pytest.raises(ValueError):
            client._validate_folder("INBOX/../secret")
        
        with pytest.raises(ValueError):
            client._validate_folder("INBOX\\..\\secret")

    def test_validate_folder_dangerous_chars(self):
        """Test folder validation blocks dangerous characters."""
        client = OutlookGraphClient(client_id="test")
        
        # Invalid characters
        with pytest.raises(ValueError):
            client._validate_folder("INBOX;rm -rf")
        
        with pytest.raises(ValueError):
            client._validate_folder("INBOX|whoami")
        
        with pytest.raises(ValueError):
            client._validate_folder("INBOX$(whoami)")

    def test_validate_uid_valid(self):
        """Test UID validation with valid IDs."""
        client = OutlookGraphClient(client_id="test")
        
        # Valid UIDs (Graph API uses GUID-like IDs)
        valid_uid = "AAMkADFiMWI0NjEzLTA3MDYtNDhkNi1hOGE0LTI5ZDg4ZjEzYjM5MwBGAAAAAAD"
        assert client._validate_uid(valid_uid) == valid_uid

    def test_validate_uid_dangerous_chars(self):
        """Test UID validation blocks dangerous characters."""
        client = OutlookGraphClient(client_id="test")
        
        with pytest.raises(ValueError):
            client._validate_uid("abc123;rm -rf")
        
        with pytest.raises(ValueError):
            client._validate_uid("abc123|whoami")
        
        with pytest.raises(ValueError):
            client._validate_uid("abc123/../secret")


class TestGraphAPIIntegration:
    """Test Graph API integration (with mocks)."""

    @patch("requests.request")
    def test_fetch_recent_with_folder_validation(self, mock_request):
        """Test fetch recent validates folder first."""
        client = OutlookGraphClient(client_id="test")
        client._token = "fake_token"
        
        # This should work
        mock_request.return_value.json.return_value = {"value": []}
        
        result = client.fetch_recent(count=10, folder="INBOX")
        assert result == []

    @patch("requests.request")
    def test_search_escapes_query(self, mock_request):
        """Test search escapes the query."""
        client = OutlookGraphClient(client_id="test")
        client._token = "fake_token"
        
        # Mock response
        mock_request.return_value.json.return_value = {"value": []}
        
        # Search with potentially dangerous query
        client.search("test' OR '1'='1")
        
        # Check that the query was escaped
        call_args = mock_request.call_args
        filter_param = call_args[1]["params"]["$filter"]
        
        # Should contain escaped single quote
        assert "test''" in filter_param or "test'" in filter_param
