"""
Query Intent Detector for Swedish Queries
Determines what the user really wants (OFFICIAL info, GUIDE, NEWS, etc.)

Examples:
  "hur ansöker man arbetstillstnd?" → GUIDE
  "vad är skillnaden mellan..." → DEFINITION
  "öppettider apotek" → PRACTICAL_INFO
  "senaste nytt om regeringen" → NEWS
  "politiker riksdagen" → INFORMATION
"""

import re
import logging
from typing import Tuple, Dict, List
from enum import Enum

logger = logging.getLogger(__name__)

class QueryIntent(Enum):
    """Types of user intents"""
    GUIDE = "guide"              # "Hur man..." - step by step
    DEFINITION = "definition"    # "Vad är..." - definition/comparison
    PRACTICAL_INFO = "practical" # "öppettider", "adress" - immediate facts
    NEWS = "news"                # "senaste nytt" - current events
    INFORMATION = "information"  # General information search
    NAVIGATION = "navigation"    # "SVT", "DN" - go to specific site
    LOCAL = "local"              # Location-based queries

class QueryIntentDetector:
    """Detects user intent from Swedish queries"""
    
    def __init__(self):
        # Swedish question words indicating intent
        self.question_patterns = {
            QueryIntent.GUIDE: [
                r'\bhur\b', r'\bpå vilka sätt\b', r'\bsteg för steg\b',
                r'\binstruktion\b', r'\bvägledning\b', r'\bprocess\b',
                r'\bprocedur\b', r'\btutorial\b',
            ],
            QueryIntent.DEFINITION: [
                r'\bvad (?:är|betyder)\b', r'\bnormal definition\b',
                r'\bskillnad mellan\b', r'\bförklaring\b',
            ],
            QueryIntent.PRACTICAL_INFO: [
                r'\böppettid\b', r'\badress\b', r'\btelefon\b',
                r'\bkontakt\b', r'\bpris\b', r'\bkostnad\b',
                r'\bkarta\b', r'\bplats\b', r'\blokalisering\b',
                r'\btimmar\b', r'\bschema\b',
            ],
            QueryIntent.NEWS: [
                r'\bsenaste nytt\b', r'\bidag\b', r'\bnyheter?\b',
                r'\bnyligen\b', r'\baknyheter\b', r'\bhändelse\b',
                r'\bevent\b', r'\bnyhetsflöde\b',
            ],
        }
        
        # Common Swedish entities that indicate location
        self.location_keywords = {
            'stockholm', 'göteborg', 'malmö', 'uppsala', 'västerås',
            'örebro', 'linköping', 'helsingborg', 'borås', 'växjö',
            'sverige', 'stockholm', 'kommun', 'lan', 'län',
        }
        
        # Swedish government/official keywords
        self.official_keywords = {
            'regeringen', 'riksdag', 'myndighet', 'lag', 'förordning',
            '.gov.se', 'kommun', 'stat', 'statsminister', 'minister',
        }
    
    def detect(self, query: str) -> Tuple[QueryIntent, float]:
        """
        Detect the intent of a Swedish query
        
        Args:
            query: Swedish search query
        
        Returns:
            (QueryIntent, confidence 0.0-1.0)
        """
        query_lower = query.lower()
        
        # Check for explicit intent patterns
        for intent, patterns in self.question_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    return (intent, 0.9)
        
        # Check for location-based (LOCAL)
        for location in self.location_keywords:
            if location in query_lower:
                return (QueryIntent.LOCAL, 0.7)
        
        # Check for official/government intent
        for keyword in self.official_keywords:
            if keyword in query_lower:
                return (QueryIntent.INFORMATION, 0.8)
        
        # Default: general information
        return (QueryIntent.INFORMATION, 0.5)
    
    def get_boost_factors(self, intent: QueryIntent) -> Dict[str, float]:
        """Get ranking boosts for specific intent"""
        boosts = {
            QueryIntent.GUIDE: {
                'freshness': 1.0,      # Don't prioritize fresh for guides
                'authority': 1.5,      # Prioritize authoritative sources
                'content_length': 2.0, # Longer articles better
            },
            QueryIntent.DEFINITION: {
                'freshness': 1.0,
                'authority': 2.0,      # Very authoritative
                'content_length': 1.5,
            },
            QueryIntent.PRACTICAL_INFO: {
                'freshness': 2.5,      # Very fresh
                'authority': 1.5,
                'content_length': 0.5, # Short summaries better
                'structure': 2.0,      # Well-structured data
            },
            QueryIntent.NEWS: {
                'freshness': 5.0,      # Extremely fresh
                'authority': 1.0,
                'content_length': 1.0,
                'pubdate': 10.0,       # Recent publication critical
            },
            QueryIntent.LOCAL: {
                'freshness': 2.0,
                'location': 10.0,      # Location critical
                'authority': 1.5,
            },
            QueryIntent.INFORMATION: {
                'freshness': 1.0,
                'authority': 1.5,
                'content_length': 1.0,
            },
        }
        return boosts.get(intent, {})
    
    def reformat_query(self, query: str, intent: QueryIntent) -> str:
        """
        Reformat query based on detected intent
        
        Examples:
            "Hur man ansöker arbetstillstånd?" → "ansöka arbetstillstånd"
            "Vad är skillnaden mellan..." → "skillnad ..."
        """
        query_lower = query.lower()
        
        # Remove question marks and common question starters
        reformatted = re.sub(r'\b(hur|vad|vilken|var|när)\b', '', query_lower)
        reformatted = re.sub(r'[?!]', '', reformatted)
        reformatted = re.sub(r'\bärvid\b', '', reformatted)
        reformatted = re.sub(r'\bär\b', '', reformatted)
        reformatted = re.sub(r'\bman\b', '', reformatted)
        reformatted = re.sub(r'\bskillnaden mellan\b', '', reformatted)
        
        # Clean up extra spaces
        reformatted = ' '.join(reformatted.split())
        
        return reformatted.strip()

# Global instance
intent_detector = QueryIntentDetector()

def detect_query_intent(query: str) -> Tuple[QueryIntent, float]:
    """Detect the intent of a Swedish query"""
    return intent_detector.detect(query)

def get_ranking_boosts(intent: QueryIntent) -> Dict[str, float]:
    """Get ranking boosts for specific intent"""
    return intent_detector.get_boost_factors(intent)

def reformat_query_for_intent(query: str, intent: QueryIntent) -> str:
    """Reformat query based on intent"""
    return intent_detector.reformat_query(query, intent)


# Test
if __name__ == "__main__":
    detector = QueryIntentDetector()
    
    test_queries = [
        "Hur ansöker man arbetstillstånd i Sverige?",
        "Vad är skillnaden mellan landsting och region?",
        "Öppettider apotek stockholm",
        "Senaste nytt om regeringen",
        "Bästa restaurang göteborg",
    ]
    
    print("Swedish Query Intent Detection:\n")
    for query in test_queries:
        intent, confidence = detector.detect(query)
        reformatted = detector.reformat_query(query, intent)
        print(f"Query: {query}")
        print(f"Intent: {intent.value} (confidence: {confidence:.2f})")
        print(f"Reformatted: {reformatted}\n")
