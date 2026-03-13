"""
Klar Search Engine - Answer Box System
Direct answer extraction for Swedish queries

Provides Google-style featured snippets with verified Swedish content.
Critical for national scale deployment and user experience.

Answer Types:
1. Facts (dates, numbers, statistics)
2. Definitions (what is X?)
3. Procedures (how to X?)
4. Lists (top X, best X)
5. Comparisons (X vs Y, difference between X and Y)
6. Government data (official information)
"""

import re
import logging
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class AnswerType(Enum):
    """Types of direct answers"""
    FACT = "fact"  # Simple factual answer
    DEFINITION = "definition"  # What is X?
    PROCEDURE = "procedure"  # How to do X?
    LIST = "list"  # Top/best items
    COMPARISON = "comparison"  # X vs Y
    LOCATION = "location"  # Where is X?
    TIME = "time"  # When/what time
    PERSON = "person"  # Who is X?
    GOVERNMENT = "government"  # Official gov data
    CALCULATION = "calculation"  # Math/conversion


@dataclass
class AnswerBox:
    """Direct answer result"""
    answer_type: AnswerType
    question: str  # Original query
    answer_text: str  # Main answer
    source_url: str  # Where answer came from
    source_title: str  # Source page title
    confidence: float  # 0-1 confidence score
    verified: bool  # Is this from official source?
    metadata: Dict  # Additional data
    last_updated: Optional[datetime] = None


class SwedishQuestionClassifier:
    """
    Classifies Swedish questions into types
    
    Patterns for Swedish questions:
    - Vad = What (definition, explanation)
    - Hur = How (procedure, method)
    - Var = Where (location)
    - När = When (time, date)
    - Varför = Why (explanation, reason)
    - Vem = Who (person, identity)
    - Vilken/Vilket = Which (choice, comparison)
    """
    
    # Question word patterns
    QUESTION_PATTERNS = {
        'vad': ['vad är', 'vad innebär', 'vad betyder', 'vad menas med'],
        'hur': ['hur', 'hur gör man', 'hur ansöker', 'hur fungerar', 'hur mycket'],
        'var': ['var finns', 'var ligger', 'var är', 'var kan'],
        'när': ['när', 'när öppnar', 'när stänger', 'vilken tid'],
        'varför': ['varför', 'varför är', 'varför kan'],
        'vem': ['vem är', 'vem var', 'vilka är'],
        'vilken': ['vilken', 'vilket', 'vilka', 'skillnad mellan', 'skillnaden mellan'],
    }
    
    # Intent patterns
    DEFINITION_PATTERNS = [
        r'vad (?:är|innebär|betyder|menas med)',
        r'definition av',
        r'förklara',
    ]
    
    PROCEDURE_PATTERNS = [
        r'hur (?:gör man|ansöker|fungerar|går det till)',
        r'hur man',
        r'steg för steg',
        r'guide för',
    ]
    
    COMPARISON_PATTERNS = [
        r'skillnad(?:en)? mellan',
        r'(?:jämför|jämförelse)',
        r'(?:\w+) vs (?:\w+)',
        r'(?:\w+) eller (?:\w+)',
    ]
    
    LOCATION_PATTERNS = [
        r'var (?:finns|ligger|är|kan man hitta)',
        r'plats för',
        r'adress till',
    ]
    
    TIME_PATTERNS = [
        r'när (?:öppnar|stänger|börjar|slutar)',
        r'öppettider',
        r'vilken tid',
        r'datum för',
    ]
    
    def classify(self, query: str) -> Tuple[AnswerType, float]:
        """
        Classify query into answer type
        
        Args:
            query: User query
            
        Returns:
            (AnswerType, confidence)
        """
        query_lower = query.lower().strip()
        
        # Check patterns in order of specificity
        
        # Comparison (very specific)
        if any(re.search(pattern, query_lower) for pattern in self.COMPARISON_PATTERNS):
            return (AnswerType.COMPARISON, 0.9)
        
        # Procedure
        if any(re.search(pattern, query_lower) for pattern in self.PROCEDURE_PATTERNS):
            return (AnswerType.PROCEDURE, 0.85)
        
        # Definition
        if any(re.search(pattern, query_lower) for pattern in self.DEFINITION_PATTERNS):
            return (AnswerType.DEFINITION, 0.85)
        
        # Location
        if any(re.search(pattern, query_lower) for pattern in self.LOCATION_PATTERNS):
            return (AnswerType.LOCATION, 0.8)
        
        # Time
        if any(re.search(pattern, query_lower) for pattern in self.TIME_PATTERNS):
            return (AnswerType.TIME, 0.8)
        
        # Simple fact (default)
        return (AnswerType.FACT, 0.5)


class AnswerExtractor:
    """
    Extracts answer snippets from documents
    
    Uses pattern matching and heuristics to find relevant
    answer passages in indexed documents.
    """
    
    def __init__(self):
        self.classifier = SwedishQuestionClassifier()
    
    def extract_definition(self, query: str, document: Dict) -> Optional[AnswerBox]:
        """
        Extract definition-style answer
        
        Pattern: "X är..." or "X innebär..." or "X betyder..."
        """
        # Extract entity being defined
        entity_match = re.search(r'vad (?:är|innebär|betyder) (.+?)(?:\?|$)', 
                                query.lower())
        if not entity_match:
            return None
        
        entity = entity_match.group(1).strip()
        
        # Search for definition patterns in document
        content = document.get('content', '')
        title = document.get('title', '')
        
        # Pattern: "Entity är/innebär/betyder ..."
        patterns = [
            rf'{re.escape(entity)} är ([^\.]+\.)',
            rf'{re.escape(entity)} innebär ([^\.]+\.)',
            rf'{re.escape(entity)} betyder ([^\.]+\.)',
            rf'{re.escape(entity.capitalize())} är ([^\.]+\.)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                answer_text = f"{entity.capitalize()} är {match.group(1)}"
                
                return AnswerBox(
                    answer_type=AnswerType.DEFINITION,
                    question=query,
                    answer_text=answer_text,
                    source_url=document.get('url', ''),
                    source_title=title,
                    confidence=0.8,
                    verified=self._is_verified_source(document.get('url', '')),
                    metadata={'entity': entity}
                )
        
        return None
    
    def extract_procedure(self, query: str, document: Dict) -> Optional[AnswerBox]:
        """
        Extract procedure/how-to answer
        
        Looks for step-by-step instructions
        """
        content = document.get('content', '')
        title = document.get('title', '')
        
        # Look for numbered steps
        steps = re.findall(r'(\d+)\.\s+([^\n]{10,200})', content)
        
        if len(steps) >= 3:
            # Format first 3-5 steps
            step_list = []
            for num, text in steps[:5]:
                step_list.append(f"{num}. {text.strip()}")
            
            answer_text = "\n".join(step_list)
            if len(steps) > 5:
                answer_text += f"\n\n(+ {len(steps) - 5} fler steg)"
            
            return AnswerBox(
                answer_type=AnswerType.PROCEDURE,
                question=query,
                answer_text=answer_text,
                source_url=document.get('url', ''),
                source_title=title,
                confidence=0.75,
                verified=self._is_verified_source(document.get('url', '')),
                metadata={'total_steps': len(steps)}
            )
        
        return None
    
    def extract_comparison(self, query: str, documents: List[Dict]) -> Optional[AnswerBox]:
        """
        Extract comparison answer
        
        Pattern: "Skillnaden mellan X och Y är..."
        """
        # Extract entities being compared
        comp_match = re.search(r'skillnad(?:en)? mellan (.+?) och (.+?)(?:\?|$)', 
                              query.lower())
        if not comp_match:
            return None
        
        entity1 = comp_match.group(1).strip()
        entity2 = comp_match.group(2).strip()
        
        # Search documents for comparison text
        for doc in documents[:5]:  # Check top 5 docs
            content = doc.get('content', '')
            
            # Look for comparison patterns
            patterns = [
                rf'skillnad(?:en)? mellan {re.escape(entity1)} och {re.escape(entity2)} (?:är|innebär) ([^\.]+\.)',
                rf'{re.escape(entity1)} ([^\.]*?) medan {re.escape(entity2)} ([^\.]+\.)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    answer_text = f"Skillnaden mellan {entity1} och {entity2}:\n\n{match.group(0)}"
                    
                    return AnswerBox(
                        answer_type=AnswerType.COMPARISON,
                        question=query,
                        answer_text=answer_text,
                        source_url=doc.get('url', ''),
                        source_title=doc.get('title', ''),
                        confidence=0.7,
                        verified=self._is_verified_source(doc.get('url', '')),
                        metadata={'entity1': entity1, 'entity2': entity2}
                    )
        
        return None
    
    def extract_government_data(self, query: str, document: Dict) -> Optional[AnswerBox]:
        """
        Extract official government data
        
        High confidence for .gov.se sources
        """
        url = document.get('url', '')
        
        # Only from verified government sources
        if not self._is_verified_source(url):
            return None
        
        content = document.get('content', '')
        title = document.get('title', '')
        
        # Extract relevant paragraph (first meaningful paragraph)
        paragraphs = [p.strip() for p in content.split('\n\n') if len(p.strip()) > 50]
        
        if paragraphs:
            answer_text = paragraphs[0][:500]  # First 500 chars
            if len(paragraphs[0]) > 500:
                answer_text += "..."
            
            return AnswerBox(
                answer_type=AnswerType.GOVERNMENT,
                question=query,
                answer_text=answer_text,
                source_url=url,
                source_title=title,
                confidence=0.95,  # High confidence for gov sources
                verified=True,
                metadata={'agency': self._extract_agency(url)},
                last_updated=document.get('last_modified')
            )
        
        return None
    
    def _is_verified_source(self, url: str) -> bool:
        """Check if source is verified/official"""
        verified_domains = [
            '.gov.se', 'riksdagen.se', 'regeringen.se',
            'migrationsverket.se', 'skatteverket.se',
            'forsakringskassan.se', 'arbetsformedlingen.se',
            '.edu.se', '.su.se', '.uu.se', '.lu.se',
            'svt.se', 'sr.se'
        ]
        
        return any(domain in url.lower() for domain in verified_domains)
    
    def _extract_agency(self, url: str) -> str:
        """Extract agency name from government URL"""
        agency_map = {
            'riksdagen.se': 'Sveriges Riksdag',
            'regeringen.se': 'Sveriges Regering',
            'migrationsverket.se': 'Migrationsverket',
            'skatteverket.se': 'Skatteverket',
            'forsakringskassan.se': 'Försäkringskassan',
            'arbetsformedlingen.se': 'Arbetsförmedlingen',
        }
        
        for domain, name in agency_map.items():
            if domain in url:
                return name
        
        return 'Myndighet'
    
    def extract_answer(self, query: str, documents: List[Dict]) -> Optional[AnswerBox]:
        """
        Main entry point - extract best answer for query
        
        Args:
            query: User query
            documents: Top search results
            
        Returns:
            AnswerBox or None
        """
        if not documents:
            return None
        
        # Classify question type
        answer_type, confidence = self.classifier.classify(query)
        
        # Try to extract answer based on type
        if answer_type == AnswerType.DEFINITION:
            return self.extract_definition(query, documents[0])
        
        elif answer_type == AnswerType.PROCEDURE:
            return self.extract_procedure(query, documents[0])
        
        elif answer_type == AnswerType.COMPARISON:
            return self.extract_comparison(query, documents)
        
        # Try government data for all types if available
        for doc in documents[:3]:
            if '.gov.se' in doc.get('url', ''):
                answer = self.extract_government_data(query, doc)
                if answer:
                    return answer
        
        return None


def format_answer_box_html(answer: AnswerBox) -> str:
    """Format answer box as HTML for display"""
    verified_badge = '✓ Verifierad källa' if answer.verified else ''
    updated_text = ''
    if answer.last_updated:
        updated_text = f'Uppdaterad: {answer.last_updated.strftime("%Y-%m-%d")}'
    
    html = f'''
    <div class="answer-box" style="
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 20px;
        margin: 20px 0;
        background: #f8f9fa;
    ">
        <div class="answer-header" style="margin-bottom: 10px;">
            {f'<span style="color: #28a745; font-weight: bold;">{verified_badge}</span>' if answer.verified else ''}
        </div>
        
        <div class="answer-content" style="
            font-size: 16px;
            line-height: 1.6;
            margin: 15px 0;
            white-space: pre-wrap;
        ">
            {answer.answer_text}
        </div>
        
        <div class="answer-footer" style="
            font-size: 14px;
            color: #666;
            border-top: 1px solid #e0e0e0;
            padding-top: 10px;
            margin-top: 15px;
        ">
            <div>Källa: <a href="{answer.source_url}" style="color: #1a0dab;">{answer.source_title}</a></div>
            {f'<div style="margin-top: 5px;">{updated_text}</div>' if updated_text else ''}
        </div>
    </div>
    '''
    
    return html


def format_answer_box_json(answer: AnswerBox) -> Dict:
    """Format answer box as JSON for API"""
    return {
        'type': answer.answer_type.value,
        'question': answer.question,
        'answer': answer.answer_text,
        'source': {
            'url': answer.source_url,
            'title': answer.source_title,
        },
        'confidence': answer.confidence,
        'verified': answer.verified,
        'metadata': answer.metadata,
        'last_updated': answer.last_updated.isoformat() if answer.last_updated else None
    }


# Singleton instance
_answer_extractor = None

def get_answer_extractor() -> AnswerExtractor:
    """Get or create answer extractor singleton"""
    global _answer_extractor
    if _answer_extractor is None:
        _answer_extractor = AnswerExtractor()
    return _answer_extractor
