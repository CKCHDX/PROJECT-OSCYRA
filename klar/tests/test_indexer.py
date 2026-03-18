"""
Tests for Indexer
Validates inverted index building and searching
"""

import pytest
import tempfile
from pathlib import Path
from indexer import InvertedIndex, IndexBuilder, DocumentInfo

class TestInvertedIndex:
    """Test inverted index operations"""
    
    def test_index_initialization(self):
        """Test that index initializes correctly"""
        index = InvertedIndex()
        assert index.num_documents == 0
        assert len(index.index) == 0
        assert len(index.documents) == 0
    
    def test_add_document(self):
        """Test adding documents to index"""
        index = InvertedIndex()
        
        doc_info = DocumentInfo(
            doc_id="doc1",
            url="https://example.se/page1",
            domain="example.se",
            title="Test Page",
            snippet="This is a test page",
            word_count=50,
            crawled_at="2026-02-05T10:00:00",
            authority_score=1.0
        )
        
        terms = ["test", "page", "example", "test"]  # "test" appears twice
        index.add_document(doc_info, terms)
        
        assert index.num_documents == 1
        assert "doc1" in index.documents
        assert "test" in index.index
        assert index.index["test"]["doc1"] == 2  # Term frequency
        assert index.index["page"]["doc1"] == 1
    
    def test_calculate_idf(self):
        """Test IDF calculation"""
        index = InvertedIndex()
        
        # Add two documents
        doc1 = DocumentInfo(
            doc_id="doc1", url="https://example.se/1", domain="example.se",
            title="Doc 1", snippet="", word_count=10,
            crawled_at="2026-02-05", authority_score=1.0
        )
        doc2 = DocumentInfo(
            doc_id="doc2", url="https://example.se/2", domain="example.se",
            title="Doc 2", snippet="", word_count=10,
            crawled_at="2026-02-05", authority_score=1.0
        )
        
        # "common" appears in both, "rare" only in doc1
        index.add_document(doc1, ["common", "rare"])
        index.add_document(doc2, ["common"])
        
        index.calculate_idf()
        
        # "rare" should have higher IDF (appears in fewer documents)
        assert index.idf_cache["rare"] > index.idf_cache["common"]
    
    def test_search(self):
        """Test basic search functionality"""
        index = InvertedIndex()
        
        doc1 = DocumentInfo(
            doc_id="doc1", url="https://example.se/riksdag", domain="example.se",
            title="Riksdagen", snippet="Sveriges riksdag", word_count=100,
            crawled_at="2026-02-05", authority_score=2.0
        )
        
        index.add_document(doc1, ["riksdag", "sverige", "politik"])
        index.calculate_idf()
        
        results = index.search(["riksdag"])
        
        assert len(results) > 0
        assert "doc1" in results
        assert results["doc1"] > 0  # Should have positive score
    
    def test_save_and_load(self, temp_data_dir):
        """Test saving and loading index"""
        index = InvertedIndex()
        
        doc1 = DocumentInfo(
            doc_id="doc1", url="https://example.se/test", domain="example.se",
            title="Test", snippet="Test page", word_count=50,
            crawled_at="2026-02-05", authority_score=1.0
        )
        
        index.add_document(doc1, ["test", "example"])
        index.calculate_idf()
        
        # Save
        save_path = temp_data_dir / "test_index.pkl"
        index.save(save_path)
        assert save_path.exists()
        
        # Load
        loaded_index = InvertedIndex.load(save_path)
        assert loaded_index.num_documents == 1
        assert "test" in loaded_index.index
        assert "doc1" in loaded_index.documents


class TestIndexBuilder:
    """Test index builder"""
    
    def test_index_builder_initialization(self):
        """Test index builder initializes"""
        builder = IndexBuilder()
        assert builder.index is not None
    
    def test_process_crawled_page(self):
        """Test processing a crawled page"""
        builder = IndexBuilder()
        
        page_data = {
            'url': 'https://www.riksdagen.se/test',
            'domain': 'riksdagen.se',
            'title': 'Test Riksdagen',
            'content': 'Sveriges riksdag beslutar om lagar.',
            'word_count': 50,
            'crawled_at': '2026-02-05T10:00:00'
        }
        
        doc_id = builder._process_page(page_data)
        
        assert doc_id is not None
        assert doc_id in builder.index.documents
        assert builder.index.num_documents == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
