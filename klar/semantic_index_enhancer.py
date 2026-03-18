"""
Klar Search Engine - Semantic-Aware Indexing Integration
Enhanced indexing with Swedish semantic understanding

This module extends the indexer to use the Swedish semantic engine
for better query processing and relevance scoring.
"""

import logging
from typing import Dict, List, Optional
from nlp_processor import nlp_processor
from swedish_semantic_engine import (
    SwedishSemanticEngine,
    AdvancedCompoundSplitter,
    SemanticQueryContext,
)

logger = logging.getLogger(__name__)


class SemanticIndexEnhancer:
    """
    Enhances indexing and search with Swedish semantic understanding.
    
    Integration points:
    1. Document processing: Extract semantic signals during indexing
    2. Query processing: Understand query intent and context
    3. Result ranking: Apply semantic-based boosts
    """
    
    def __init__(self):
        self.semantic_engine = SwedishSemanticEngine()
        self.compound_splitter = AdvancedCompoundSplitter()
        logger.info("Semantic Index Enhancer initialized")
    
    def process_document_for_indexing(self, doc_url: str, doc_title: str, doc_content: str) -> Dict:
        """
        Process document during indexing to extract semantic signals
        
        Returns:
            Dictionary with:
            - basic_terms: Standard indexed terms
            - semantic_terms: Additional terms from semantic analysis
            - content_category: OFFICIAL, GUIDE, NEWS, etc.
            - authority_signals: Geographic/institutional relevance
        """
        result = {
            'basic_terms': [],
            'semantic_terms': [],
            'content_category': 'GENERAL',
            'is_official': False,
            'geographic_scope': None,
            'institutions': [],
            'authority_boost': 1.0,
        }
        
        # 1. Basic NLP processing
        processed = nlp_processor.process_query(doc_title + " " + doc_content[:500])
        result['basic_terms'] = processed['stems']
        
        # 2. Detect if document is official/government
        url_lower = doc_url.lower()
        if '.gov.se' in url_lower or any(agency in url_lower for agency in 
                ['migrationsverket', 'skatteverket', 'riksdagen', 'regeringen']):
            result['is_official'] = True
            result['authority_boost'] = 3.0
            result['content_category'] = 'OFFICIAL'
        
        # 3. Compound word analysis for better recall
        title_words = doc_title.lower().split()
        for word in title_words:
            compounds = self.compound_splitter.split_recursive(word)
            result['semantic_terms'].extend(compounds)
        
        # 4. Geographic extraction
        context = self.semantic_engine.extract_semantic_context(doc_title)
        if context.geographic_scope:
            result['geographic_scope'] = context.geographic_scope
        if context.mentioned_institutions:
            result['institutions'] = context.mentioned_institutions
        
        # 5. Content category detection (basic)
        if 'guide' in doc_content.lower() or 'hur ' in doc_title.lower():
            result['content_category'] = 'GUIDE'
        elif 'definition' in doc_content.lower() or 'vad är' in doc_title.lower():
            result['content_category'] = 'DEFINITION'
        elif 'news' in doc_url.lower() or 'nyheter' in doc_url.lower():
            result['content_category'] = 'NEWS'
        
        return result
    
    def process_query_semantically(self, query: str) -> Dict:
        """
        Process query using semantic understanding
        
        Returns:
            Dictionary with:
            - search_terms: Terms to search for
            - context: SemanticQueryContext with ranking factors
            - ranking_boost: Overall multiplier for results
        """
        # Extract semantic context
        context = self.semantic_engine.extract_semantic_context(query)
        
        # Process query with NLP
        nlp_result = nlp_processor.process_query(query)
        
        # Expand with compound splitting
        all_search_terms = set(nlp_result['stems'])
        for term in nlp_result['filtered_tokens']:
            compounds = self.compound_splitter.split_recursive(term)
            all_search_terms.update(compounds)
        
        # Add expansions
        all_search_terms.update(nlp_result.get('expanded_terms', []))
        
        return {
            'search_terms': list(all_search_terms),
            'original_terms': nlp_result['stems'],
            'expanded_terms': nlp_result.get('expanded_terms', []),
            'context': context,
            'ranking_boost': self.semantic_engine.get_ranking_factors(context),
            'intent': context.intent_category,
        }
    
    def calculate_semantic_relevance_boost(self, query_context: SemanticQueryContext, 
                                          document_info: Dict) -> float:
        """
        Calculate semantic relevance boost for a document given query context
        
        Factors:
        - Official content for official queries: +3.0x
        - Geographic match: +2.0x
        - Content category match: +1.5x
        - Institutional alignment: +1.5x
        """
        boost = 1.0
        
        # Official query matching official content
        if query_context.is_official_query and document_info.get('is_official'):
            boost *= 3.0
        
        # Geographic match
        if query_context.geographic_scope and document_info.get('geographic_scope'):
            if query_context.geographic_scope.lower() == document_info['geographic_scope'].lower():
                boost *= 2.0
        
        # Content category match with intent
        content_cat = document_info.get('content_category', 'GENERAL')
        intent = query_context.intent_category
        
        category_matches = {
            ('OFFICIAL', 'OFFICIAL'): 2.0,
            ('GUIDE', 'GUIDE'): 1.8,
            ('NEWS', 'NEWS'): 2.5,
            ('DEFINITION', 'DEFINITION'): 1.5,
            ('PRACTICAL_INFO', 'PRACTICAL_INFO'): 1.8,
            ('LOCAL', 'LOCAL'): 2.0,
        }
        
        if (content_cat, intent) in category_matches:
            boost *= category_matches[(content_cat, intent)]
        
        # Institutional alignment
        if query_context.mentioned_institutions and document_info.get('institutions'):
            matched = set(query_context.mentioned_institutions) & set(document_info['institutions'])
            if matched:
                boost *= 1.5
        
        return boost
    
    def get_semantic_answer_boost(self, query_context: SemanticQueryContext) -> Dict[str, float]:
        """
        Get boosts for featured/answer box content based on query
        
        Favors:
        - Official definitions for DEFINITION intent
        - Step-by-step guides for GUIDE intent
        - Fresh news for NEWS intent
        - Local results for LOCAL intent
        """
        boosts = {
            'DEFINITION': {
                'prefer_content_length': 'moderate',
                'prefer_source': 'official',
                'freshness_weight': 0.1,
                'authority_weight': 0.9,
            },
            'GUIDE': {
                'prefer_content_length': 'long',
                'prefer_source': 'any',
                'freshness_weight': 0.2,
                'authority_weight': 0.7,
            },
            'NEWS': {
                'prefer_content_length': 'short',
                'prefer_source': 'media',
                'freshness_weight': 0.9,
                'authority_weight': 0.1,
            },
            'PRACTICAL_INFO': {
                'prefer_content_length': 'short',
                'prefer_source': 'any',
                'freshness_weight': 0.8,
                'authority_weight': 0.2,
            },
            'OFFICIAL': {
                'prefer_content_length': 'any',
                'prefer_source': 'official',
                'freshness_weight': 0.3,
                'authority_weight': 0.9,
            },
        }
        
        return boosts.get(query_context.intent_category, {})


class QueryReformulator:
    """
    Reformulates queries for better matching based on semantic understanding
    
    Examples:
        "Hur ansöker man arbetstillstand?" → ["ansöka", "arbetstillstand"]
        "Vad är skillnaden mellan..." → ["skillnad", "mellan", ...]
        "Systembolaget öppettider" → ["systembolaget", "öppet", "timmar", "hours"]
    """
    
    def __init__(self):
        self.semantic_engine = SwedishSemanticEngine()
    
    def reformulate(self, query: str, context: SemanticQueryContext) -> List[str]:
        """
        Generate query reformulations based on intent
        """
        reformulations = []
        query_lower = query.lower()
        
        # GUIDE: Remove procedural markers, keep main topic
        if context.intent_category == 'GUIDE':
            # Remove "hur man", "steg för steg", etc.
            reformed = query_lower
            for pattern in ['hur (?:kan|gör|man|skulle)', 'steg för steg', 'instruktion']:
                reformed = reformed.replace(pattern, '')
            reformulations.append(reformed.strip())
        
        # DEFINITION: Focus on terms being compared
        elif context.intent_category == 'DEFINITION':
            # Extract terms from "skillnad mellan X och Y"
            import re
            match = re.search(r'mellan\s+(.+?)\s+(?:och|eller)\s+(.+?)(?:\?|$)', query_lower)
            if match:
                reformulations.extend([match.group(1).strip(), match.group(2).strip()])
        
        # PRACTICAL_INFO: Add synonyms for common searches
        elif context.intent_category == 'PRACTICAL_INFO':
            if 'öppet' in query_lower or 'öppettid' in query_lower:
                reformulations.extend(['öppet', 'timmar', 'hours', 'klocka'])
            if 'adress' in query_lower or 'lokalisering' in query_lower:
                reformulations.extend(['address', 'plats', 'väg', 'street'])
            if 'telefon' in query_lower or 'nummer' in query_lower:
                reformulations.extend(['phone', 'ring', 'call'])
        
        return reformulations


# Global instance for easy access
semantic_enhancer = SemanticIndexEnhancer()
query_reformulator = QueryReformulator()


def test_semantic_indexing():
    """Test semantic indexing enhancement"""
    enhancer = SemanticIndexEnhancer()
    
    # Test document processing
    test_doc = {
        'url': 'https://www.migrationsverket.se/English/Private-individuals/Work/Work-permit.html',
        'title': 'Work permit Sweden',
        'content': 'How to apply for a work permit in Sweden. Step-by-step guide...',
    }
    
    result = enhancer.process_document_for_indexing(test_doc['url'], test_doc['title'], test_doc['content'])
    logger.info(f"Document processing result:\n{result}\n")
    
    # Test query processing
    test_queries = [
        "Hur ansöker man arbetstillstand i Sverige?",
        "Öppettider systembolaget stockholm",
        "Senaste nytt om regeringen",
    ]
    
    for query in test_queries:
        result = enhancer.process_query_semantically(query)
        logger.info(f"Query: {query}")
        logger.info(f"  Intent: {result['intent']}")
        logger.info(f"  Search terms: {result['search_terms'][:5]}...")
        logger.info(f"  Ranking boost: {result['ranking_boost']['combined_score']:.2f}\n")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_semantic_indexing()
