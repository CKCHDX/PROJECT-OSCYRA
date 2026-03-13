#!/usr/bin/env python3
"""
Test NLP and Search Integration
Tests if natural language queries are properly reformulated and searched
"""

import requests
import json
import time

API_URL = "http://localhost:5000"

def test_nlp_search():
    """Test natural language search queries"""
    
    test_queries = [
        {
            "query": "Hur ansöker jag arbetstillståndet?",
            "expected": "Should find immigration/work permit pages",
            "category": "Government/Procedural"
        },
        {
            "query": "Var kan jag hitta sjukhus i Stockholm?",
            "expected": "Should find health/hospital pages",
            "category": "Health/Location"
        },
        {
            "query": "Vad är öppettiderna idag?",
            "expected": "Should find service/opening hours",
            "category": "Services"
        },
        {
            "query": "Hur ansöker man universitet?",
            "expected": "Should find education/admission pages",
            "category": "Education"
        },
        {
            "query": "riksdagsledamöter",
            "expected": "Should find parliament/member pages",
            "category": "Government"
        },
        {
            "query": "apotek",
            "expected": "Should find pharmacy pages",
            "category": "Health"
        },
    ]
    
    print("\n" + "="*80)
    print("  KLAR SEARCH ENGINE - NLP & SEARCH INTEGRATION TEST")
    print("="*80 + "\n")
    
    for i, test in enumerate(test_queries, 1):
        print(f"\n[TEST {i}] {test['category']}")
        print(f"Query: {test['query']}")
        print(f"Expected: {test['expected']}")
        print("-" * 80)
        
        try:
            # Make search request
            response = requests.get(
                f"{API_URL}/api/search",
                params={"q": test['query'], "limit": 5},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Show NLP optimization details
                print(f"✓ Response received ({data.get('time_ms', 'N/A')}ms)")
                print(f"\nNLP Optimization:")
                print(f"  Original query: {data.get('query', 'N/A')}")
                print(f"  Optimized query: {data.get('optimized_query', 'N/A')}")
                print(f"  Search terms: {data.get('search_terms', 'N/A')}")
                print(f"  Intent detected: {data.get('intent', 'N/A')} (confidence: {data.get('intent_confidence', 'N/A')})")
                print(f"  Cached: {data.get('cached', False)}")
                
                # Show results
                results = data.get('results', [])
                print(f"\nResults: {data.get('count', 0)} shown / {data.get('total_matches', 0)} total")
                
                if results:
                    print("\nTop 3 Results:")
                    for idx, result in enumerate(results[:3], 1):
                        print(f"\n  {idx}. {result.get('title', 'No title')[:60]}")
                        print(f"     URL: {result.get('url', 'N/A')}")
                        print(f"     Score: {result.get('score', 0):.4f}")
                        if 'snippet' in result:
                            snippet = result['snippet'][:100].replace('\n', ' ')
                            print(f"     Snippet: {snippet}...")
                else:
                    print("\n  ⚠ NO RESULTS FOUND")
                    print("  This may indicate:")
                    print("    - Not enough pages crawled yet")
                    print("    - NLP reformulation too aggressive")
                    print("    - Index doesn't contain relevant terms")
            else:
                print(f"✗ Error: HTTP {response.status_code}")
                print(f"  Response: {response.text[:200]}")
                
        except requests.exceptions.ConnectionError:
            print("✗ ERROR: Cannot connect to API server")
            print("  Make sure the server is running: python api_server.py")
            return False
        except Exception as e:
            print(f"✗ ERROR: {e}")
        
        time.sleep(0.5)  # Brief pause between requests
    
    print("\n" + "="*80)
    print("  TEST COMPLETE")
    print("="*80)
    return True

def test_index_stats():
    """Check index statistics"""
    print("\n" + "="*80)
    print("  INDEX STATISTICS")
    print("="*80)
    
    try:
        response = requests.get(f"{API_URL}/api/stats", timeout=5)
        if response.status_code == 200:
            stats = response.json()
            print(f"\n  Documents indexed: {stats.get('num_documents', 'N/A')}")
            print(f"  Unique terms: {stats.get('num_terms', 'N/A')}")
            print(f"  Average doc length: {stats.get('avg_doc_length', 'N/A')} words")
            print(f"  Cache hit rate: {stats.get('cache_hit_rate', 'N/A')}")
        else:
            print(f"\n  ✗ Stats endpoint returned {response.status_code}")
    except Exception as e:
        print(f"\n  ⚠ Could not fetch stats: {e}")
    
    print("="*80 + "\n")

if __name__ == "__main__":
    print("\nStarting NLP & Search Integration Test...")
    print("This will test if natural language queries are properly processed\n")
    
    # Test stats first
    test_index_stats()
    
    # Test NLP search
    test_nlp_search()
    
    print("\n✓ Test script complete\n")
    print("Next steps:")
    print("  1. If NO RESULTS: The crawler needs to run longer to index more pages")
    print("  2. If results look poor: Check NLP reformulation is working properly")
    print("  3. Re-run crawler with new settings: python quick_init.py")
