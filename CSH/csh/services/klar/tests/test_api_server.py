"""
Tests for API Server
Validates REST API endpoints and responses
"""

import pytest
import json
from unittest.mock import Mock, patch
from api_server import app

@pytest.fixture
def client():
    """Create test client"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


class TestHealthEndpoint:
    """Test /api/health endpoint"""
    
    def test_health_check(self, client):
        """Test that health endpoint returns OK"""
        response = client.get('/api/health')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert 'timestamp' in data


class TestSearchEndpoint:
    """Test /api/search endpoint"""
    
    @patch('api_server.SearchEngineAPI.search')
    def test_search_with_query(self, mock_search, client):
        """Test search with valid query"""
        # Mock search results
        mock_search.return_value = {
            'results': [
                {
                    'url': 'https://www.riksdagen.se',
                    'title': 'Riksdagen',
                    'snippet': 'Sveriges riksdag',
                    'score': 95
                }
            ],
            'count': 1,
            'query': 'riksdagen',
            'time_ms': 45.2
        }
        
        response = client.get('/api/search?q=riksdagen')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'results' in data
        assert 'count' in data
        assert 'query' in data
        assert data['query'] == 'riksdagen'
    
    def test_search_without_query(self, client):
        """Test search without query parameter"""
        response = client.get('/api/search')
        assert response.status_code == 400  # Bad request
        
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_search_with_empty_query(self, client):
        """Test search with empty query"""
        response = client.get('/api/search?q=')
        assert response.status_code == 400
        
        data = json.loads(response.data)
        assert 'error' in data
    
    @patch('api_server.SearchEngineAPI.search')
    def test_search_pagination(self, mock_search, client):
        """Test search with pagination parameters"""
        mock_search.return_value = {
            'results': [],
            'count': 0,
            'query': 'test',
            'time_ms': 10.0
        }
        
        response = client.get('/api/search?q=test&page=2&per_page=20')
        assert response.status_code == 200


class TestSuggestEndpoint:
    """Test /api/suggest endpoint"""
    
    @patch('api_server.SearchEngineAPI.suggest')
    def test_suggest_with_query(self, mock_suggest, client):
        """Test autocomplete suggestions"""
        mock_suggest.return_value = {
            'suggestions': ['riksdagen', 'riksdagsledamot', 'riksdagsval'],
            'query': 'riks'
        }
        
        response = client.get('/api/suggest?q=riks')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'suggestions' in data
        assert len(data['suggestions']) > 0
    
    def test_suggest_without_query(self, client):
        """Test suggest without query"""
        response = client.get('/api/suggest')
        assert response.status_code == 400


class TestStatsEndpoint:
    """Test /api/stats endpoint"""
    
    def test_stats_endpoint(self, client):
        """Test system statistics endpoint"""
        response = client.get('/api/stats')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'index' in data
        assert 'system' in data


class TestRateLimiting:
    """Test rate limiting functionality"""
    
    @patch('api_server.SearchEngineAPI.search')
    def test_rate_limit_enforcement(self, mock_search, client):
        """Test that rate limiting blocks excessive requests"""
        mock_search.return_value = {
            'results': [],
            'count': 0,
            'query': 'test',
            'time_ms': 1.0
        }
        
        # Make many requests rapidly
        for i in range(65):  # Over limit of 60
            response = client.get(f'/api/search?q=test{i}')
            
            if i < 60:
                assert response.status_code == 200
            else:
                # Should be rate limited
                assert response.status_code == 429


class TestCORS:
    """Test CORS headers"""
    
    def test_cors_headers_present(self, client):
        """Test that CORS headers are set"""
        response = client.get('/api/health')
        assert 'Access-Control-Allow-Origin' in response.headers


class TestErrorHandling:
    """Test error handling"""
    
    def test_404_handler(self, client):
        """Test 404 error handler"""
        response = client.get('/nonexistent-endpoint')
        assert response.status_code == 404
        
        data = json.loads(response.data)
        assert 'error' in data


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
