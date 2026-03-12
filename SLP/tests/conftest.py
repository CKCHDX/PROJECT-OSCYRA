"""
Pytest configuration and fixtures.
"""

import pytest
from pathlib import Path


@pytest.fixture
def config_dir():
    """Provide path to config directory."""
    return Path(__file__).parent.parent / "config"


@pytest.fixture
def temp_config(tmp_path):
    """Create temporary config directory."""
    return tmp_path / "config"
