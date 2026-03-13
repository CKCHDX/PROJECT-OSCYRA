#!/usr/bin/env python3
"""
Test script for MediaWiki API integration.
Run this to verify the Wikipedia search functionality works correctly.
"""

import requests

def test_wikipedia_api():
    """Test Swedish Wikipedia API access."""
    print("Testing Swedish Wikipedia MediaWiki API Integration")
    print("="*50)
    print()
    
    WIKI_API = "https://sv.wikipedia.org/w/api.php"
    
    # Test 1: Search API
    print("Test 1: Search API (Stockholm)")
    params = {
        'action': 'query',
        'format': 'json',
        'list': 'search',
        'srsearch': 'Stockholm',
        'srlimit': 3,
        'srprop': 'snippet',
        'utf8': 1
    }
    
    try:
        response = requests.get(WIKI_API, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            results = data.get('query', {}).get('search', [])
            print(f"  ✓ Found {len(results)} results:")
            for r in results:
                print(f"    - {r.get('title')}")
        else:
            print(f"  ✗ API returned status {response.status_code}")
    except Exception as e:
        print(f"  ✗ Error: {e}")
    
    print()
    
    # Test 2: OpenSearch API
    print("Test 2: OpenSearch API (Sverige)")
    opensearch_params = {
        'action': 'opensearch',
        'search': 'Sverige',
        'limit': 5,
        'namespace': 0,
        'format': 'json'
    }
    
    try:
        response = requests.get(WIKI_API, params=opensearch_params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            titles = data[1] if len(data) > 1 else []
            print(f"  ✓ Found {len(titles)} results:")
            for i, title in enumerate(titles[:3], 1):
                print(f"    {i}. {title}")
        else:
            print(f"  ✗ API returned status {response.status_code}")
    except Exception as e:
        print(f"  ✗ Error: {e}")
    
    print()
    
    # Test 3: Test various queries
    print("Test 3: Multiple search queries")
    test_queries = [
        'Gustav Vasa',
        'Minecraft',
        'Python programmeringsspråk',
        'Stockholm stad'
    ]
    
    for query in test_queries:
        try:
            response = requests.get(WIKI_API, 
                                   params={**opensearch_params, 'search': query, 'limit': 3}, 
                                   timeout=10)
            if response.status_code == 200:
                data = response.json()
                count = len(data[1]) if len(data) > 1 else 0
                print(f"  '{query}': {count} results")
            else:
                print(f"  '{query}': API error")
        except Exception as e:
            print(f"  '{query}': {str(e)}")
    
    print()
    print("="*50)
    print("Testing complete!")
    print()
    print("If all tests passed, Wikipedia integration is working.")
    print("You can now run 'uvicorn main:app --reload' to start the backend.")

if __name__ == "__main__":
    test_wikipedia_api()
