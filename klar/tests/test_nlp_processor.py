"""
Tests for NLP Processor
Validates Swedish language processing capabilities
"""

import pytest
from nlp_processor import (
    SwedishCompoundSplitter,
    SwedishSynonymExpander,
    SwedishQuestionClassifier,
    SwedishNLPProcessor
)

class TestSwedishCompoundSplitter:
    """Test compound word splitting"""
    
    def test_riksdag_compound(self):
        """Test riksdagsledamot splits correctly"""
        splitter = SwedishCompoundSplitter()
        result = splitter.split("riksdagsledamot")
        assert "riksdag" in result
        assert "ledamot" in result
    
    def test_arbetstillstand_compound(self):
        """Test arbetstillstånd splits correctly"""
        splitter = SwedishCompoundSplitter()
        result = splitter.split("arbetstillstånd")
        assert "arbete" in result or "arbeta" in result
        assert "tillstånd" in result
    
    def test_non_compound_word(self):
        """Test that simple words are not split"""
        splitter = SwedishCompoundSplitter()
        result = splitter.split("student")
        assert len(result) == 0  # No valid splits


class TestSwedishSynonymExpander:
    """Test synonym expansion"""
    
    def test_jobb_synonyms(self):
        """Test that jobb expands to work-related terms"""
        expander = SwedishSynonymExpander()
        synonyms = expander.expand("jobb")
        assert "arbete" in synonyms or len(synonyms) > 0
    
    def test_unknown_word(self):
        """Test handling of unknown words"""
        expander = SwedishSynonymExpander()
        synonyms = expander.expand("xyzabc123")
        assert len(synonyms) == 0


class TestSwedishQuestionClassifier:
    """Test question type classification"""
    
    def test_vad_question(self):
        """Test VAD (what) questions"""
        classifier = SwedishQuestionClassifier()
        q_type = classifier.classify("Vad är riksdagen?")
        assert q_type == "VAD"
    
    def test_hur_question(self):
        """Test HUR (how) questions"""
        classifier = SwedishQuestionClassifier()
        q_type = classifier.classify("Hur ansöker man svenskt medborgarskap?")
        assert q_type == "HUR"
    
    def test_var_question(self):
        """Test VAR (where) questions"""
        classifier = SwedishQuestionClassifier()
        q_type = classifier.classify("Var ligger Stockholm?")
        assert q_type == "VAR"
    
    def test_non_question(self):
        """Test non-question text"""
        classifier = SwedishQuestionClassifier()
        q_type = classifier.classify("Svenska nyheter idag")
        assert q_type == "NONE"


class TestSwedishNLPProcessor:
    """Test complete NLP pipeline"""
    
    def test_tokenization(self):
        """Test Swedish tokenization"""
        processor = SwedishNLPProcessor()
        tokens = processor.tokenize("Detta är ett test.")
        assert "detta" in [t.lower() for t in tokens]
        assert "test" in [t.lower() for t in tokens]
    
    def test_stopword_removal(self):
        """Test Swedish stopword removal"""
        processor = SwedishNLPProcessor()
        words = ["detta", "är", "ett", "viktigt", "test"]
        filtered = processor.remove_stopwords(words)
        assert "viktigt" in filtered
        assert "test" in filtered
        assert "är" not in filtered  # Stopword should be removed
        assert "ett" not in filtered  # Stopword should be removed
    
    def test_stemming(self):
        """Test Swedish stemming"""
        processor = SwedishNLPProcessor()
        stemmed = processor.stem("restauranger")
        # Should stem to "restaurang" or similar
        assert len(stemmed) <= len("restauranger")
    
    def test_full_processing(self):
        """Test complete NLP pipeline"""
        processor = SwedishNLPProcessor()
        result = processor.process_query("Hur ansöker man arbetstillstånd i Sverige?")
        
        assert result['original_query'] == "Hur ansöker man arbetstillstånd i Sverige?"
        assert result['question_type'] == "HUR"
        assert len(result['processed_terms']) > 0
        assert result['intent'] in ['OFFICIAL', 'GUIDE', 'DEFINITION']


class TestCategoryDetection:
    """Test category detection"""
    
    def test_official_category(self):
        """Test detection of official/government queries"""
        processor = SwedishNLPProcessor()
        result = processor.process_query("riksdagen nya lagar")
        assert result['category'] == 'OFFICIAL'
    
    def test_news_category(self):
        """Test detection of news queries"""
        processor = SwedishNLPProcessor()
        result = processor.process_query("senaste nyheterna idag")
        assert result['category'] == 'NEWS'
    
    def test_guide_category(self):
        """Test detection of guide/how-to queries"""
        processor = SwedishNLPProcessor()
        result = processor.process_query("hur man ansöker pass")
        assert result['category'] == 'GUIDE'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
