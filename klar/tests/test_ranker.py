"""
Tests for Ranker
Validates ranking algorithm and score calculation
"""

import pytest
from ranker import RankingSignals, RankingEngine, PageRankCalculator
from indexer import DocumentInfo

class TestRankingSignals:
    """Test ranking signals dataclass"""
    
    def test_signals_creation(self):
        """Test creating ranking signals"""
        signals = RankingSignals(
            tf_idf=0.8,
            pagerank=0.6,
            authority=0.9,
            recency=0.7,
            density=0.5,
            structure=0.4,
            swedish_boost=1.2
        )
        
        assert signals.tf_idf == 0.8
        assert signals.authority == 0.9
    
    def test_final_score_calculation(self):
        """Test final score calculation with weights"""
        signals = RankingSignals(
            tf_idf=1.0,
            pagerank=1.0,
            authority=1.0,
            recency=1.0,
            density=1.0,
            structure=1.0,
            swedish_boost=1.0
        )
        
        score = signals.final_score()
        assert 0 <= score <= 100  # Score should be normalized


class TestPageRankCalculator:
    """Test PageRank calculation"""
    
    def test_pagerank_simple_graph(self):
        """Test PageRank on simple graph"""
        # Create simple link graph: A -> B, B -> C, C -> A
        link_graph = {
            'pageA': ['pageB'],
            'pageB': ['pageC'],
            'pageC': ['pageA']
        }
        
        calculator = PageRankCalculator(link_graph)
        pagerank_scores = calculator.calculate(iterations=10)
        
        # All pages should have similar scores (equal structure)
        assert abs(pagerank_scores['pageA'] - pagerank_scores['pageB']) < 0.1
        assert abs(pagerank_scores['pageB'] - pagerank_scores['pageC']) < 0.1
        
        # Scores should sum to approximately 1.0
        total = sum(pagerank_scores.values())
        assert 0.9 < total < 1.1
    
    def test_pagerank_hub_page(self):
        """Test PageRank with hub page (many incoming links)"""
        link_graph = {
            'page1': ['hub'],
            'page2': ['hub'],
            'page3': ['hub'],
            'hub': []
        }
        
        calculator = PageRankCalculator(link_graph)
        scores = calculator.calculate(iterations=20)
        
        # Hub should have highest score
        assert scores['hub'] > scores['page1']
        assert scores['hub'] > scores['page2']
        assert scores['hub'] > scores['page3']


class TestRankingEngine:
    """Test complete ranking engine"""
    
    def test_ranking_engine_initialization(self):
        """Test ranking engine initializes"""
        from indexer import InvertedIndex
        
        index = InvertedIndex()
        engine = RankingEngine(index)
        
        assert engine.index is not None
    
    def test_authority_boost_government(self):
        """Test authority boost for .gov.se domains"""
        from indexer import InvertedIndex
        
        index = InvertedIndex()
        engine = RankingEngine(index)
        
        # Add government document
        gov_doc = DocumentInfo(
            doc_id="gov1",
            url="https://www.riksdagen.se/test",
            domain="riksdagen.se",
            title="Riksdagen",
            snippet="Official government site",
            word_count=100,
            crawled_at="2026-02-05",
            authority_score=1.0
        )
        
        # Add regular document
        regular_doc = DocumentInfo(
            doc_id="reg1",
            url="https://example.se/test",
            domain="example.se",
            title="Example",
            snippet="Regular site",
            word_count=100,
            crawled_at="2026-02-05",
            authority_score=1.0
        )
        
        gov_signals = engine._calculate_signals("gov1", gov_doc, 0.5, "test")
        reg_signals = engine._calculate_signals("reg1", regular_doc, 0.5, "test")
        
        # Government site should have higher authority
        assert gov_signals.authority > reg_signals.authority
    
    def test_recency_boost(self):
        """Test recency boost for fresh content"""
        from indexer import InvertedIndex
        from datetime import datetime, timedelta
        
        index = InvertedIndex()
        engine = RankingEngine(index)
        
        # Fresh document (today)
        fresh_doc = DocumentInfo(
            doc_id="fresh",
            url="https://example.se/fresh",
            domain="example.se",
            title="Fresh News",
            snippet="Today's news",
            word_count=100,
            crawled_at=datetime.now().isoformat(),
            authority_score=1.0
        )
        
        # Old document (1 year ago)
        old_doc = DocumentInfo(
            doc_id="old",
            url="https://example.se/old",
            domain="example.se",
            title="Old News",
            snippet="Last year's news",
            word_count=100,
            crawled_at=(datetime.now() - timedelta(days=365)).isoformat(),
            authority_score=1.0
        )
        
        fresh_signals = engine._calculate_signals("fresh", fresh_doc, 0.5, "news")
        old_signals = engine._calculate_signals("old", old_doc, 0.5, "news")
        
        # Fresh content should have higher recency score
        assert fresh_signals.recency > old_signals.recency


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
