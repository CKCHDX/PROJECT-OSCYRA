"""
Pytest Configuration and Fixtures
Shared test utilities for KSE test suite
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Generator

@pytest.fixture
def temp_data_dir() -> Generator[Path, None, None]:
    """Create a temporary data directory for testing"""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_crawled_page():
    """Sample crawled page data for testing"""
    return {
        'url': 'https://www.riksdagen.se/sv/dokument-lagar/',
        'domain': 'riksdagen.se',
        'title': 'Dokument & lagar - Riksdagen',
        'content': 'Sveriges riksdag beslutar om lagar och statsbudget. Här kan du följa riksdagens arbete.',
        'html': '<html><head><title>Dokument & lagar - Riksdagen</title></head><body>Sveriges riksdag beslutar om lagar och statsbudget.</body></html>',
        'links': ['https://www.riksdagen.se/sv/', 'https://www.riksdagen.se/sv/ledamoter-partier/'],
        'meta_description': 'Sveriges riksdag',
        'meta_keywords': 'riksdag, lagar, politik',
        'language': 'sv',
        'status_code': 200,
        'crawled_at': '2026-02-05T10:00:00',
        'content_hash': 'abc123def456',
        'word_count': 150,
        'headers': {'content-type': 'text/html; charset=utf-8'}
    }


@pytest.fixture
def sample_search_query():
    """Sample search query for testing"""
    return {
        'query': 'svenska riksdagen lagar',
        'expected_terms': ['svensk', 'riksdag', 'lag'],
        'category': 'OFFICIAL'
    }
