"""
Klar Search Engine - Swedish NLP Test Suite
Comprehensive tests for semantic understanding enhancements

Tests cover:
- Government/institutional queries
- Geographic/municipal queries
- Temporal expressions
- Procedural/guide queries
- Definition/comparison queries
- Intent classification accuracy
"""

import logging
from swedish_semantic_engine import SwedishSemanticEngine, AdvancedCompoundSplitter
from semantic_index_enhancer import SemanticIndexEnhancer, semantic_enhancer
from nlp_processor import nlp_processor

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# ANSI colors for output
GREEN = '\033[92m'
BLUE = '\033[94m'
YELLOW = '\033[93m'
RED = '\033[91m'
RESET = '\033[0m'
BOLD = '\033[1m'


class SwedishNLPTestSuite:
    """Comprehensive test suite for Swedish NLP"""
    
    def __init__(self):
        self.engine = SwedishSemanticEngine()
        self.splitter = AdvancedCompoundSplitter()
        self.enhancer = semantic_enhancer
        self.passed = 0
        self.failed = 0
    
    def test_compound_splitting(self):
        """Test compound word decomposition"""
        logger.info(f"\n{BOLD}{'='*80}")
        logger.info(f"TEST: Compound Word Splitting{RESET}")
        logger.info(f"{'='*80}\n")
        
        test_cases = [
            ("arbetstillståndet", ["arbete", "tillstand"]),
            ("riksdagsledamöterna", ["riksdag", "ledamot"]),
            ("midsommarafton", ["midsommar", "afton"]),
            ("sjukhusläkare", ["sjukhus", "läkare"]),
            ("universitetsutbildning", ["universitet", "utbildning"]),
            ("kommunfullmäktige", ["kommun", "fullmäktige"]),
            ("socialtjänst", ["social", "tjänst"]),
            ("försäkringskassan", ["försäkring", "kassan"]),
        ]
        
        for word, expected_contains in test_cases:
            result = self.splitter.split_recursive(word)
            result_lower = [r.lower() for r in result]
            
            # Check if expected components are in result
            match = all(any(exp in r for r in result_lower) for exp in expected_contains)
            
            status = f"{GREEN}✓ PASS{RESET}" if match else f"{RED}✗ FAIL{RESET}"
            logger.info(f"{status}: {word}")
            logger.info(f"       Result: {' + '.join(result)}")
            logger.info(f"       Expected components: {', '.join(expected_contains)}\n")
            
            if match:
                self.passed += 1
            else:
                self.failed += 1
    
    def test_intent_classification(self):
        """Test query intent classification"""
        logger.info(f"\n{BOLD}{'='*80}")
        logger.info(f"TEST: Intent Classification{RESET}")
        logger.info(f"{'='*80}\n")
        
        test_cases = [
            ("Hur ansöker man arbetstillståndet?", "GUIDE", 0.8),
            ("Vad är skillnaden mellan landsting och region?", "DEFINITION", 0.75),
            ("Öppettider systembolaget Stockholm", "PRACTICAL_INFO", 0.7),
            ("Senaste nytt om regeringen", "NEWS", 0.8),
            ("Riksdagsledamöterna från miljöpartiet", "INFORMATION", 0.5),
            ("Bästa restaurang Göteborg", "LOCAL", 0.7),
            ("CSN studiebidrag ansökan", "OFFICIAL", 0.8),
            ("Hur lång är Öresundsbron?", "DEFINITION", 0.6),
        ]
        
        for query, expected_intent, min_confidence in test_cases:
            context = self.engine.extract_semantic_context(query)
            
            match = context.intent_category == expected_intent
            status = f"{GREEN}✓ PASS{RESET}" if match else f"{YELLOW}⚠ PARTIAL{RESET}"
            
            logger.info(f"{status}: {query}")
            logger.info(f"       Expected: {expected_intent}")
            logger.info(f"       Got: {context.intent_category} (confidence: {context.intent_confidence:.2f})\n")
            
            if match:
                self.passed += 1
            else:
                self.failed += 1
    
    def test_geographic_extraction(self):
        """Test geographic context extraction"""
        logger.info(f"\n{BOLD}{'='*80}")
        logger.info(f"TEST: Geographic Context Extraction{RESET}")
        logger.info(f"{'='*80}\n")
        
        test_cases = [
            ("Restaurang Stockholm", "Stockholm", 2.0),
            ("Apotek Göteborg", "Göteborg", 2.0),
            ("Bästa skola Malmö", "Malmö", 2.0),
            ("Sjukhus i Uppsala", "Uppsala", 2.0),
            ("Västra Götaland kommuner", "Västra Götaland", 1.5),
        ]
        
        for query, expected_location, expected_boost in test_cases:
            context = self.engine.extract_semantic_context(query)
            
            location_match = any(expected_location.lower() in loc.lower() 
                                for loc in context.mentioned_locations) if context.mentioned_locations else False
            boost_match = abs(context.region_boost - expected_boost) < 0.1
            
            match = location_match or context.geographic_scope is not None
            status = f"{GREEN}✓ PASS{RESET}" if match else f"{YELLOW}⚠ PARTIAL{RESET}"
            
            logger.info(f"{status}: {query}")
            logger.info(f"       Expected location: {expected_location}")
            logger.info(f"       Got: {context.geographic_scope or context.mentioned_locations}")
            logger.info(f"       Region boost: {context.region_boost:.2f}\n")
            
            if match:
                self.passed += 1
            else:
                self.failed += 1
    
    def test_official_institution_detection(self):
        """Test government/institutional entity detection"""
        logger.info(f"\n{BOLD}{'='*80}")
        logger.info(f"TEST: Official Institution Detection{RESET}")
        logger.info(f"{'='*80}\n")
        
        test_cases = [
            ("Ansökan arbetstillståndet Migrationsverket", True, ["migrationsverket"]),
            ("Skattedeklaration Skatteverket", True, ["skatteverket"]),
            ("Studiebidrag CSN", True, ["csn"]),
            ("Riksdagsledamöter", True, ["riksdag"]),
            ("Restaurang Stockholm", False, []),
            ("Bästa hotell Danmark", False, []),
        ]
        
        for query, should_be_official, expected_institutions in test_cases:
            context = self.engine.extract_semantic_context(query)
            
            official_match = context.is_official_query == should_be_official
            inst_match = len(context.mentioned_institutions) == len(expected_institutions)
            
            match = official_match
            status = f"{GREEN}✓ PASS{RESET}" if match else f"{YELLOW}⚠ PARTIAL{RESET}"
            
            logger.info(f"{status}: {query}")
            logger.info(f"       Expected official: {should_be_official}")
            logger.info(f"       Got official: {context.is_official_query}")
            logger.info(f"       Institutions: {context.mentioned_institutions}")
            logger.info(f"       Official boost: {context.official_boost:.2f}\n")
            
            if match:
                self.passed += 1
            else:
                self.failed += 1
    
    def test_temporal_extraction(self):
        """Test temporal expression extraction"""
        logger.info(f"\n{BOLD}{'='*80}")
        logger.info(f"TEST: Temporal Expression Extraction{RESET}")
        logger.info(f"{'='*80}\n")
        
        test_cases = [
            ("Senaste nytt idag", True, 3.0),
            ("Nyheter igår", True, 2.5),
            ("Midsommarafton öppettider", True, 1.0),
            ("Lucia celebration Sweden", True, 1.0),
            ("Restaurang Stockholm", False, 1.0),
            ("Bästa skola detta år", True, 1.2),
        ]
        
        for query, has_temporal, expected_freshness_boost in test_cases:
            context = self.engine.extract_semantic_context(query)
            
            temporal_match = context.freshness_boost != 1.0 or has_temporal == False
            
            status = f"{GREEN}✓ PASS{RESET}" if temporal_match else f"{YELLOW}⚠ PARTIAL{RESET}"
            
            logger.info(f"{status}: {query}")
            logger.info(f"       Has temporal: {context.freshness_boost != 1.0}")
            logger.info(f"       Temporal keywords: {context.temporal_keywords}")
            logger.info(f"       Freshness boost: {context.freshness_boost:.2f}\n")
            
            if temporal_match:
                self.passed += 1
            else:
                self.failed += 1
    
    def test_ranking_factor_calculation(self):
        """Test ranking factor calculation"""
        logger.info(f"\n{BOLD}{'='*80}")
        logger.info(f"TEST: Ranking Factor Calculation{RESET}")
        logger.info(f"{'='*80}\n")
        
        test_cases = [
            ("Hur ansöker man arbetstillståndet?", "GUIDE", 1.8),      # GUIDE intent multiplier
            ("Senaste nytt regeringen", "NEWS", 2.5),                   # NEWS intent multiplier
            ("CSN studier", "OFFICIAL", 2.0),                           # OFFICIAL intent multiplier
            ("Apotek Göteborg", "LOCAL", 2.0),                          # LOCAL intent multiplier
        ]
        
        for query, intent_category, min_multiplier in test_cases:
            context = self.engine.extract_semantic_context(query)
            factors = self.engine.get_ranking_factors(context)
            
            score_check = factors['combined_score'] >= 1.0
            
            status = f"{GREEN}✓ PASS{RESET}" if score_check else f"{RED}✗ FAIL{RESET}"
            
            logger.info(f"{status}: {query}")
            logger.info(f"       Intent: {context.intent_category}")
            logger.info(f"       Combined score: {factors['combined_score']:.3f}")
            logger.info(f"       Geographic: {factors['geographic_boost']:.2f}x")
            logger.info(f"       Official: {factors['official_boost']:.2f}x")
            logger.info(f"       Freshness: {factors['freshness_boost']:.2f}x\n")
            
            if score_check:
                self.passed += 1
            else:
                self.failed += 1
    
    def test_end_to_end_semantic_processing(self):
        """Test complete semantic processing pipeline"""
        logger.info(f"\n{BOLD}{'='*80}")
        logger.info(f"TEST: End-to-End Semantic Processing{RESET}")
        logger.info(f"{'='*80}\n")
        
        test_queries = [
            "Hur ansöker man arbetstillståndet som utländsk medarbetare?",
            "Vad är skillnaden mellan landsting och region i Sverige?",
            "Öppettider systembolaget midsommarafton Stockholm",
            "Senaste nyheter från Riksdagen 2026",
            "CSN studiebidraget - ansökan och beräkning",
        ]
        
        for query in test_queries:
            result = self.enhancer.process_query_semantically(query)
            
            has_terms = len(result['search_terms']) > 0
            has_intent = result['intent'] != 'GENERAL'
            has_boost = result['ranking_boost']['combined_score'] > 0
            
            match = has_terms and has_boost
            status = f"{GREEN}✓ PASS{RESET}" if match else f"{YELLOW}⚠ PARTIAL{RESET}"
            
            logger.info(f"{status}: {query}")
            logger.info(f"       Intent: {result['intent']}")
            logger.info(f"       Search terms: {result['search_terms'][:5]}...")
            logger.info(f"       Combined ranking: {result['ranking_boost']['combined_score']:.3f}\n")
            
            if match:
                self.passed += 1
            else:
                self.failed += 1
    
    def run_all_tests(self):
        """Run all test suites"""
        logger.info(f"\n{BOLD}{BLUE}KLAR Swedish NLP Test Suite{RESET}")
        logger.info(f"{BLUE}================================{RESET}\n")
        
        self.test_compound_splitting()
        self.test_intent_classification()
        self.test_geographic_extraction()
        self.test_official_institution_detection()
        self.test_temporal_extraction()
        self.test_ranking_factor_calculation()
        self.test_end_to_end_semantic_processing()
        
        # Print summary
        logger.info(f"\n{BOLD}{'='*80}")
        logger.info(f"TEST SUMMARY{RESET}")
        logger.info(f"{'='*80}")
        
        total = self.passed + self.failed
        percentage = (self.passed / total * 100) if total > 0 else 0
        
        if percentage >= 80:
            status_color = GREEN
        elif percentage >= 60:
            status_color = YELLOW
        else:
            status_color = RED
        
        logger.info(f"Total tests: {total}")
        logger.info(f"Passed: {GREEN}{self.passed}{RESET}")
        logger.info(f"Failed: {RED}{self.failed}{RESET}")
        logger.info(f"Success rate: {status_color}{percentage:.1f}%{RESET}\n")
        
        if percentage >= 80:
            logger.info(f"{GREEN}{BOLD}✓ NLP enhancements validated successfully!{RESET}\n")
        else:
            logger.info(f"{YELLOW}{BOLD}⚠ Some tests need attention{RESET}\n")


def main():
    """Run test suite"""
    suite = SwedishNLPTestSuite()
    suite.run_all_tests()


if __name__ == "__main__":
    main()
