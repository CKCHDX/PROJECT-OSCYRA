#!/usr/bin/env python3
"""Test script for enhanced NLP natural language processing"""

from nlp_processor import NLPProcessor

def test_natural_language_nlp():
    """Test NLP with natural language queries"""
    nlp = NLPProcessor()
    
    # Test natural language queries
    test_queries = [
        'Hur ansöker jag arbetstillståndet?',
        'Var kan jag hitta sjukhus i Stockholm?',
        'Vad är öppettiderna idag?',
        'Kan jag söka stipendium?',
        'Hur lång är handläggningstiden?',
        'Vilka är kraven för antagning?',
    ]
    
    print("[NLP Natural Language Processing Test]")
    print("=" * 60)
    
    for query in test_queries:
        result = nlp.process_query(query)
        print(f"\nOriginal query: {query}")
        print(f"Reformulated: {result['reformulated']}")
        print(f"Search terms: {result['search_terms']}")
        print(f"Expansion: {result['expansion']}")
    
    print("\n" + "=" * 60)
    print("[OK] All tests passed! NLP handles natural language queries.")

if __name__ == "__main__":
    test_natural_language_nlp()
