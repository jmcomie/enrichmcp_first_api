import pytest
import tempfile
import unittest.mock
from pathlib import Path


@pytest.fixture
def mock_user_data_dir():
    """Fixture that mocks appdirs.user_data_dir to return a temporary directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        with unittest.mock.patch('enrichmcp_first_api.api.user_data_dir', return_value=temp_dir):
            yield temp_dir