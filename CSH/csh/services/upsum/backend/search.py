from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
import requests
import re
from typing import List, Dict, Set

router = APIRouter()

# Swedish Wikipedia API endpoint
WIKI_API = "https://sv.wikipedia.org/w/api.php"

# User-Agent header required by Wikipedia API
HEADERS = {
    'User-Agent': 'Upsum/1.0 (https://oscyra.solutions/upsum; alex@oscyra.solutions) Python/requests'
}

# Swedish linguistic patterns
SWEDISH_DEFINITENESS = {
    'en': '',   # en bil -> bil
    'ett': '',  # ett hus -> hus
    'den': '',  # den stora bilen -> stora bilen
    'det': '',  # det stora huset -> stora huset
    'de': '',   # de stora bilarna -> stora bilarna
}

# Common Swedish suffixes for definiteness
DEFINITE_SUFFIXES = ['en', 'et', 'n', 't', 'a', 'na', 'orna', 'erna', 'arna']

# Swedish question words and natural language patterns
QUESTION_PATTERNS = [
    (r'^vad är\s+', ''),           # "vad är Stockholm" -> "Stockholm"
    (r'^vem är\s+', ''),           # "vem är Gustav Vasa" -> "Gustav Vasa"
    (r'^var ligger\s+', ''),        # "var ligger Stockholm" -> "Stockholm"
    (r'^när grundades\s+', ''),    # "när grundades Sverige" -> "Sverige"
    (r'^hur fungerar\s+', ''),      # "hur fungerar" -> direct search
    (r'^varför\s+', ''),           # "varför" -> keep as is
    (r'^beskriv\s+', ''),           # "beskriv Stockholm" -> "Stockholm"
    (r'^förklara\s+', ''),         # "förklara kvantfysik" -> "kvantfysik"
    (r'^vad betyder\s+', ''),       # "vad betyder" -> term
]

# Common Swedish compound word patterns for splitting hints
COMPOUND_HINTS = [
    'historia',  # Sveriges historia
    'stad',      # Stockholm stad
    'landet',    # Sverige landet
    'kung',      # Gustav kung
]

def normalize_swedish_query(query: str) -> List[str]:
    """
    Normalize Swedish input using linguistic rules.
    Returns multiple query variants for better search coverage.
    
    Args:
        query: Raw Swedish query
    
    Returns:
        List of normalized query variants
    """
    variants = [query]  # Always include original
    normalized = query.lower().strip()
    
    # Remove question patterns (NIL - Natural Input Language)
    for pattern, replacement in QUESTION_PATTERNS:
        if re.match(pattern, normalized, re.IGNORECASE):
            cleaned = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE).strip()
            if cleaned and cleaned not in variants:
                variants.append(cleaned)
            normalized = cleaned
            break
    
    # Remove articles and definiteness markers
    words = normalized.split()
    if len(words) > 1:
        # Remove leading articles
        if words[0] in SWEDISH_DEFINITENESS:
            article_removed = ' '.join(words[1:])
            if article_removed not in variants:
                variants.append(article_removed)
    
    # Handle definite forms (remove suffixes)
    if len(words) == 1 and len(words[0]) > 4:
        base_word = words[0]
        for suffix in DEFINITE_SUFFIXES:
            if base_word.endswith(suffix) and len(base_word) > len(suffix) + 2:
                indefinite = base_word[:-len(suffix)]
                if indefinite not in variants and len(indefinite) > 2:
                    variants.append(indefinite)
    
    # Add compound word variants
    for hint in COMPOUND_HINTS:
        if hint in normalized and len(words) > 1:
            without_hint = normalized.replace(hint, '').strip()
            if without_hint and without_hint not in variants:
                variants.append(without_hint)
    
    # Capitalize proper nouns (Swedish convention)
    if len(words) > 0:
        capitalized = ' '.join(word.capitalize() for word in words)
        if capitalized not in variants:
            variants.append(capitalized)
    
    return variants

def clean_html(text: str) -> str:
    """Remove HTML tags from text."""
    clean = re.sub(r'<[^>]+>', '', text)
    return clean.strip()

def clean_snippet(text: str, max_length: int = 200) -> str:
    """Clean and truncate text for snippet display."""
    # Remove extra whitespace and newlines
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Truncate to max_length
    if len(text) > max_length:
        text = text[:max_length].rsplit(' ', 1)[0] + '…'
    
    return text

def search_wikipedia(query: str, limit: int = 10) -> List[Dict[str, str]]:
    """
    Search Swedish Wikipedia using MediaWiki API with Swedish NLP preprocessing.
    
    Args:
        query: Search query in Swedish
        limit: Maximum number of results to return
    
    Returns:
        List of dictionaries containing title, snippet, and url
    """
    results = []
    seen_titles: Set[str] = set()
    
    # Generate query variants using Swedish linguistic rules
    query_variants = normalize_swedish_query(query)
    print(f"[NLP] Query variants: {query_variants}")
    
    try:
        # Try each query variant
        for variant in query_variants:
            if len(results) >= limit:
                break
            
            # Search API
            params = {
                'action': 'query',
                'format': 'json',
                'list': 'search',
                'srsearch': variant,
                'srlimit': limit - len(results),
                'srprop': 'snippet',
                'utf8': 1
            }
            
            response = requests.get(WIKI_API, params=params, headers=HEADERS, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                search_results = data.get('query', {}).get('search', [])
                
                for result in search_results:
                    title = result.get('title', '')
                    
                    # Skip duplicates
                    if title in seen_titles:
                        continue
                    
                    seen_titles.add(title)
                    snippet = clean_html(result.get('snippet', 'Läs mer på Wikipedia'))
                    
                    # Construct Wikipedia URL
                    url = f"https://sv.wikipedia.org/wiki/{title.replace(' ', '_')}"
                    
                    results.append({
                        'title': title,
                        'snippet': clean_snippet(snippet),
                        'url': url
                    })
                    
                    if len(results) >= limit:
                        break
        
        # If no results, try opensearch API with first variant
        if not results and query_variants:
            opensearch_params = {
                'action': 'opensearch',
                'search': query_variants[0],
                'limit': limit,
                'namespace': 0,
                'format': 'json'
            }
            
            response = requests.get(WIKI_API, params=opensearch_params, headers=HEADERS, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                titles = data[1] if len(data) > 1 else []
                descriptions = data[2] if len(data) > 2 else []
                urls = data[3] if len(data) > 3 else []
                
                for i, title in enumerate(titles):
                    if title in seen_titles:
                        continue
                    
                    seen_titles.add(title)
                    snippet = descriptions[i] if i < len(descriptions) and descriptions[i] else 'Läs mer på Wikipedia'
                    url = urls[i] if i < len(urls) else f"https://sv.wikipedia.org/wiki/{title.replace(' ', '_')}"
                    
                    results.append({
                        'title': title,
                        'snippet': clean_snippet(snippet),
                        'url': url
                    })
        
    except requests.RequestException as e:
        print(f"Wikipedia API error: {e}")
    except Exception as e:
        print(f"Search error: {e}")
    
    return results

@router.get("/search")
def search(q: str = Query("", description="Fråga eller ämne på svenska")):
    """
    Search endpoint for Swedish Wikipedia with Natural Input Language support.
    
    Understands:
    - Natural questions ("Vad är Stockholm?", "Vem är Gustav Vasa?")
    - Definite/indefinite forms ("bilen" -> "bil")
    - Articles ("en bil" -> "bil")
    - Compound words
    - Colloquial phrasing
    
    Returns relevant Wikipedia articles based on the query.
    """
    if not q or q.strip() == "":
        return JSONResponse({"results": [], "count": 0})
    
    # Perform Wikipedia search with Swedish NLP
    results = search_wikipedia(q.strip(), limit=10)
    
    return JSONResponse({
        "results": results,
        "count": len(results),
        "query": q
    })
