"""
Klar Search Engine - Swedish NLP Processor
Enterprise-Grade Natural Language Processing for Swedish

Features:
- Swedish tokenization (handles åäö, compound words)
- Compound word splitting (riksdagsledamot → riksdag + ledamot)
- Lemmatization (restauranger → restaurang)
- Stopword removal (och, det, är, etc.)
- Swedish synonym expansion
- Entity extraction (Person, Place, Organization, Time)
- Query understanding (question type, intent classification)
"""

import re
import logging
from functools import lru_cache
from typing import List, Set, Dict, Tuple, Optional
from collections import Counter
from dataclasses import dataclass

import nltk
from nltk.tokenize import word_tokenize
from nltk.stem.snowball import SnowballStemmer

from config import SWEDISH_STOPWORDS, MIN_WORD_LENGTH, MAX_WORD_LENGTH

# Setup logging
logger = logging.getLogger(__name__)

# Initialize Swedish stemmer
swedish_stemmer = SnowballStemmer("swedish")

# Download required NLTK data (run once)
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)


@dataclass
class ProcessedText:
    """Result of NLP processing"""
    original: str
    tokens: List[str]  # Individual words
    stems: List[str]  # Stemmed words
    filtered_tokens: List[str]  # After stopword removal
    compounds_split: List[str]  # Compound words split
    entities: Dict[str, List[str]]  # Detected entities
    term_frequencies: Dict[str, int]  # Word frequencies
    

class SwedishQueryOptimizer:
    """
    Optimizes natural language queries for better search results.
    Handles: Query expansion, synonym replacement, question reformulation.
    User doesn't need to type exact keywords - just natural language.
    Supports: Questions, procedural queries, location queries, definitions.
    """
    
    # Comprehensive Swedish synonyms and related terms
    SYNONYM_MAP = {
        # === COMMON ACTIONS ===
        "hitta": ["sök", "leta", "söka", "lokalisera", "search", "find"],
        "ansöka": ["ansökan", "application", "applicera", "register"],
        "registrera": ["registration", "anmäl", "anmälan", "reg"],
        "få": ["erhålla", "obtain", "get", "hämta"],
        "skicka": ["submit", "submit", "send", "framlägg"],
        "kontakta": ["ring", "call", "contact", "kommunicera"],
        
        # === HOW/PROCESS QUERIES ===
        "hur": ["sättet", "processen", "stegen", "metoden", "vägen", "process"],
        "steg": ["steps", "stadier", "process", "etapper", "instruktioner"],
        "ansökan": ["ansöka", "application", "ansökningsprocess"],
        "process": ["processer", "förfarande", "procedure", "arbetssätt"],
        
        # === GOVERNMENT/OFFICIAL ===
        "riksdag": ["parlament", "parliament", "folkvalda", "ledamöter"],
        "regering": ["government", "regeringen", "statsministern", "ministrar"],
        "kommun": ["municipality", "kommunfullmäktige", "kommun.se", "lokalt"],
        "region": ["landsting", "regionen", "läns", "regionalt", "district"],
        "myndighet": ["authority", "statlig", "offentlig", "agency"],
        "lag": ["lag", "lagstiftning", "legislation", "rättsligt"],
        "arbetstillstand": ["arbetstillståndet", "work permit", "residence"],
        "visum": ["visa", "entry", "inresetillstånd"],
        "pasport": ["passport", "pass", "identification"],
        
        # === HEALTH & MEDICAL ===
        "sjukhus": ["hospital", "klinik", "medicin", "sjukvård", "healthcare"],
        "läkare": ["doktor", "doctor", "physician", "medicin", "lare"],
        "sjukdom": ["sjukdomar", "illness", "disease", "hälsa", "sickness"],
        "symptom": ["symptoms", "tecken", "disease", "illness"],
        "medicin": ["mediciner", "läkemedel", "medicine", "drug", "apotek"],
        "apotek": ["pharmacy", "apoteket", "medicin", "medicines"],
        "vaccination": ["vaccin", "vaccine", "immunisering", "skyddsinjection"],
        "tandvard": ["tandläkare", "dental", "teeth", "oral"],
        "1177": ["health information", "vårdguide", "healthinfo"],
        
        # === EDUCATION ===
        "skola": ["school", "utbildning", "studies", "lärande", "education"],
        "universitet": ["university", "högskola", "college", "campus"],
        "studera": ["studies", "utbildning", "kurs", "course", "education"],
        "antagning": ["admission", "antagningsprocess", "apply", "enrollment"],
        "stipendium": ["scholarship", "grant", "economic support", "bidrag"],
        "examen": ["degree", "diploma", "avslutning", "graduation"],
        
        # === WORK & EMPLOYMENT ===
        "arbete": ["jobb", "job", "work", "employment", "sysselsättning"],
        "anställning": ["anställd", "employment", "job", "position"],
        "löneökning": ["salary increase", "wage", "lön", "raise"],
        "arbetslös": ["unemployment", "jobless", "utan arbete", "lediga"],
        "cv": ["resume", "curriculum vitae", "livsöversikt"],
        "jobbsökning": ["job search", "lediga jobb", "vacancy"],
        "kollektivavtal": ["collective agreement", "avtal", "contract"],
        
        # === TRANSPORTATION ===
        "tag": ["train", "jarnvag", "railways", "sj", "transport"],
        "buss": ["bus", "bussar", "public transport", "kollektivtrafik"],
        "bil": ["car", "automobile", "vehicle", "motor"],
        "taxi": ["cab", "transportation", "ride"],
        "cykel": ["bicycle", "bike", "cycling"],
        "parkering": ["parking", "park", "vehicle"],
        "vag": ["road", "street", "motorway", "highway"],
        
        # === LOCATION/GEOGRAPHY ===
        "stad": ["city", "town", "centre", "centrum", "stadsdelar"],
        "stockholm": ["sthlm", "huvudstad", "capital", "town"],
        "göteborg": ["gothenburg", "gbg", "västra", "west"],
        "malmö": ["city", "south", "skåne", "southern"],
        "uppsala": ["town", "university", "north"],
        "norge": ["norway", "norsk", "scandinavian"],
        "danmark": ["denmark", "dansk", "scandinavian"],
        "finland": ["finland", "finnish", "nordisk"],
        
        # === SERVICES & UTILITIES ===
        "öppettider": ["opening hours", "öppet", "stängt", "timmar", "hours"],
        "adress": ["address", "plats", "lokalisering", "location"],
        "telefon": ["phone", "nummer", "ring", "call", "contact"],
        "mail": ["email", "mail", "epost", "message"],
        "hemsida": ["website", "web", "homepage", "internet"],
        "kostnad": ["price", "kostnad", "avgift", "fee", "pris"],
        "gratis": ["free", "kostnadsfritt", "no charge"],
        
        # === TIME/TEMPORAL ===
        "idag": ["today", "denna dag", "aktuell"],
        "imorgon": ["tomorrow", "nästa dag"],
        "igår": ["yesterday", "föregående dag"],
        "vecka": ["week", "veckan", "weekly"],
        "månad": ["month", "monthly", "månad"],
        "år": ["year", "annual", "årlig"],
        "senaste": ["latest", "recent", "nyligen", "senast"],
        "kommande": ["upcoming", "nästa", "future", "framtida"],
    }
    
    # Extended question patterns
    QUESTION_PATTERNS = {
        "hur": [
            r"^hur\s+(?:kan|gör|skulle|man)?\s+(.+?)\s*\??$",              # Hur kan jag...?
            r"^hur\s+(?:många|mycket|långt|stor|liten)\s+(.+?)\s*\??$",   # Hur många...?
            r"^hur\s+(?:länge|ofta|varma)\s+(.+?)\s*\??$",                # Hur länge...?
            r"^hur\s+ansöker\s+(.+?)\s*\??$",                             # Hur ansöker man...?
        ],
        "vad": [
            r"^vad\s+(?:är|betyder|kravs)\s+(.+?)\s*\??$",                # Vad är...?
            r"^vad\s+(?:görs|gör)\s+(.+?)\s*\??$",                        # Vad gör...?
            r"^vilken\s+(?:är|var)\s+(.+?)\s*\??$",                       # Vilken är...?
        ],
        "var": [
            r"^var\s+(?:kan|ligger|är|finns|hittar)\s+(.+?)\s*\??$",      # Var ligger...?
            r"^var\s+hittar\s+jag\s+(.+?)\s*\??$",                        # Var hittar jag...?
            r"^var\s+ansöker\s+(.+?)\s*\??$",                             # Var ansöker...?
        ],
        "när": [
            r"^när\s+(?:öppnar|stänger|är|börjar|slutar)\s+(.+?)\s*\??$", # När öppnar...?
            r"^vilken\s+tid\s+(?:öppnar|stänger|är)\s+(.+?)\s*\??$",     # Vilken tid öppnar...?
        ],
        "vem": [
            r"^vem\s+(?:är|var|kan)\s+(.+?)\s*\??$",                      # Vem är...?
            r"^vems\s+(.+?)\s*\??$",                                      # Vems...?
        ],
        "varför": [
            r"^varför\s+(.+?)\s*\??$",                                    # Varför...?
        ],
        "kan": [
            r"^kan\s+(?:jag|man)\s+(.+?)\s*\??$",                         # Kan jag...?
        ],
    }
    
    def __init__(self):
        self.stemmer = SnowballStemmer("swedish")
    
    def expand_query(self, query: str) -> str:
        """Expand query with synonyms and related terms for better coverage"""
        words = query.lower().split()
        expanded = []
        seen = set()
        
        for word in words:
            clean_word = word.strip(".,;:?!")
            if clean_word:
                expanded.append(clean_word)
                seen.add(clean_word)
                
                # Add synonyms for this word
                for key, synonyms in self.SYNONYM_MAP.items():
                    if clean_word == key:
                        for syn in synonyms:
                            if syn not in seen:
                                expanded.append(syn)
                                seen.add(syn)
                    elif clean_word in synonyms and key not in seen:
                        expanded.append(key)
                        seen.add(key)
        
        return " ".join(expanded)
    
    def reformulate_question(self, query: str) -> str:
        """Convert question format to search query format"""
        query_lower = query.lower().strip()
        
        # Remove question mark if present
        if query_lower.endswith("?"):
            query_lower = query_lower[:-1].strip()
        
        # Remove common question starters (more comprehensive)
        starters = [
            # Hur-questions
            "hur kan jag ", "hur gör jag ", "hur skulle jag ", 
            "hur kan man ", "hur gör man ", "hur blir ",
            "hur är det med ", "hur ansöker ",
            
            # Vad-questions  
            "vad är ", "vad betyder ", "vad kravs ", "vad gör ",
            "vilken är ", "vilka är ",
            
            # Var-questions
            "var ligger ", "var kan jag ", "var hittar jag ",
            "var ansöker ", "var är ", "var finns ",
            
            # När-questions
            "när öppnar ", "när stänger ", "när är ", "när börjar ",
            "vilken tid öppnar ", "vilken tid stänger ",
            
            # Kan-questions
            "kan jag ", "kan man ",
            
            # Varför-questions
            "varför ", "varför är "
        ]
        
        for starter in starters:
            if query_lower.startswith(starter):
                query_lower = query_lower[len(starter):].strip()
                break
        
        return query_lower
    
    def optimize_for_natural_language(self, query: str) -> Dict[str, str]:
        """
        Optimize a natural language query for search.
        Returns multiple variants for broader matching.
        Example: "Hur ansöker jag arbetstillståndet?" → "ansöka arbetstillstand"
        """
        reformulated = self.reformulate_question(query)
        expanded = self.expand_query(reformulated)
        
        return {
            "original": query,
            "reformulated": reformulated,
            "expanded": expanded,
            "search_variant_1": reformulated,  # Question as statement
            "search_variant_2": expanded,       # With synonyms and related terms
        }



class NLPProcessor:
    """Main NLP processor combining all components"""
    
    def __init__(self):
        self.compound_splitter = SwedishCompoundSplitter()
        self.query_optimizer = SwedishQueryOptimizer()
        self.stemmer = SnowballStemmer("swedish")
    
    def process_query(self, query: str) -> Dict:
        """Process a natural language query for search"""
        # Step 1: Optimize for natural language
        optimization = self.query_optimizer.optimize_for_natural_language(query)
        
        # Step 2: Tokenize the reformulated query
        reformulated = optimization["reformulated"]
        tokens = word_tokenize(reformulated.lower())
        
        # Step 3: Remove stopwords
        filtered_tokens = [t for t in tokens if t.isalpha() and len(t) > 2 
                          and t not in SWEDISH_STOPWORDS]
        
        # Step 4: Split compound words
        compounds = []
        for token in filtered_tokens:
            split = self.compound_splitter.split(token)
            compounds.extend(split)
        
        # Step 5: Stem all terms
        stems = [self.stemmer.stem(t) for t in compounds]
        
        # Remove duplicates while preserving order
        unique_stems = []
        seen = set()
        for s in stems:
            if s not in seen:
                unique_stems.append(s)
                seen.add(s)
        
        return {
            "original": query,
            "reformulated": reformulated,
            "tokens": tokens,
            "filtered_tokens": filtered_tokens,
            "compounds": compounds,
            "stems": unique_stems,
            "search_terms": unique_stems,  # Terms to search for
            "expansion": optimization["expanded"],
        }


class SwedishCompoundSplitter:
    """Splits Swedish compound words into component parts"""
    
    # Common Swedish compound patterns and joining letters
    JOINING_LETTERS = ['s', 'e', 'o', '']
    
    # Common Swedish word components (for validation)
    COMMON_COMPONENTS = {
        # Government/Politics
        'riks', 'dag', 'ledamot', 'regering', 'minister', 'stat', 'län', 
        'kommun', 'lands', 'ting', 'region', 'folk', 'myndighet',
        
        # Places
        'stad', 'borg', 'hamn', 'holm', 'köping', 'by', 'torp', 'berg',
        
        # Common words
        'arbete', 'tillstånd', 'hem', 'sida', 'tid', 'rum', 'hus', 'plats',
        'skola', 'bok', 'bibliotek', 'data', 'web', 'system', 'net',
        'telefon', 'mobil', 'bil', 'buss', 'tåg', 'flyg', 'båt',
        
        # Nature
        'sjö', 'å', 'älv', 'berg', 'dal', 'skog', 'mark', 'vatten',
        
        # Time
        'dag', 'natt', 'morgon', 'kväll', 'år', 'månad', 'vecka',
        
        # Actions
        'sök', 'hitta', 'läs', 'skriv', 'köp', 'sälj', 'arbeta', 'studera',
        
        # Qualities
        'stor', 'liten', 'ny', 'gammal', 'god', 'dålig', 'bra', 'fin',
    }
    
    def __init__(self):
        # Build reverse component index for faster lookup
        self.min_component_length = 3
    
    def is_likely_component(self, word: str) -> bool:
        """Check if a string is likely a valid Swedish word component"""
        if len(word) < self.min_component_length:
            return False
        if word in self.COMMON_COMPONENTS:
            return True
        # Additional heuristics could be added here
        return len(word) >= 4  # Longer words more likely to be real
    
    def split(self, word: str) -> List[str]:
        """Attempt to split a compound word into components"""
        if len(word) < 8:  # Too short to be compound
            return [word]
        
        word_lower = word.lower()
        
        # Try to find split points
        best_split = [word]
        best_score = 0
        
        # Try different split positions
        for i in range(3, len(word_lower) - 3):
            for joining in self.JOINING_LETTERS:
                if joining and i + len(joining) < len(word_lower):
                    # Check if joining letter matches
                    if word_lower[i:i+len(joining)] == joining:
                        left = word_lower[:i]
                        right = word_lower[i+len(joining):]
                    else:
                        continue
                else:
                    left = word_lower[:i]
                    right = word_lower[i:]
                
                # Check if both parts are likely valid
                if self.is_likely_component(left) and self.is_likely_component(right):
                    score = min(len(left), len(right))  # Favor balanced splits
                    if score > best_score:
                        best_score = score
                        best_split = [left, right]
                        
                        # Try recursive split on right part
                        right_split = self.split(right)
                        if len(right_split) > 1:
                            best_split = [left] + right_split
        
        return best_split


class SwedishSynonymExpander:
    """Expands Swedish words with synonyms for better search recall"""
    
    # Hand-curated Swedish synonym sets
    SYNONYMS = {
        # Work/Employment
        'jobb': ['arbete', 'anställning', 'sysselsättning', 'tjänst'],
        'arbete': ['jobb', 'anställning', 'sysselsättning'],
        'anställning': ['jobb', 'arbete', 'tjänst'],
        
        # Home/Housing
        'bostad': ['hem', 'lägenhet', 'hus', 'boende'],
        'hem': ['bostad', 'hus', 'boende'],
        'lägenhet': ['bostad', 'hem', 'boende'],
        
        # School/Education
        'skola': ['utbildning', 'lärande', 'undervisning'],
        'utbildning': ['skola', 'studier', 'undervisning'],
        'universitet': ['högskola', 'akademi'],
        'högskola': ['universitet', 'akademi'],
        
        # Government
        'regering': ['kabinett', 'statsråd'],
        'riksdag': ['parlament', 'riksdagen'],
        'kommun': ['kommunen', 'stad', 'stadsområde'],
        
        # Common verbs
        'söka': ['leta', 'hitta', 'sök'],
        'hitta': ['finna', 'upptäcka', 'söka'],
        'köpa': ['inhandla', 'förvärva', 'köp'],
        'sälja': ['avyttra', 'försälja', 'sälj'],
        
        # Time
        'idag': ['nu', 'nuvarande', 'aktuellt'],
        'igår': ['i går', 'förra'],
        'imorgon': ['i morgon', 'kommande'],
        
        # Common adjectives
        'stor': ['big', 'omfattande', 'betydande'],
        'liten': ['pytteliten', 'minimal', 'obetydlig'],
        'bra': ['god', 'fin', 'utmärkt', 'bäst'],
        'dålig': ['undermålig', 'inferior', 'sämst'],
        
        # Money/Finance
        'pengar': ['kontanter', 'medel', 'finanser', 'kapital'],
        'pris': ['kostnad', 'avgift', 'summa'],
        'betala': ['erlägga', 'betalning'],
        
        # Health
        'sjuk': ['ill', 'sjukdom', 'ohälsa'],
        'hälsa': ['välbefinnande', 'hälsotillstånd'],
        'läkare': ['doktor', 'medicinska'],
        
        # Information
        'information': ['info', 'uppgifter', 'data'],
        'nyhet': ['nyheter', 'aktuellt', 'notis'],
        'artikel': ['text', 'inlägg', 'dokument'],
    }
    
    def expand(self, word: str) -> Set[str]:
        """Get synonyms for a word"""
        word_lower = word.lower()
        if word_lower in self.SYNONYMS:
            return set([word_lower] + self.SYNONYMS[word_lower])
        return {word_lower}


class SwedishQuestionClassifier:
    """Classifies Swedish questions by type"""
    
    QUESTION_PATTERNS = {
        'WHAT': ['vad', 'vilken', 'vilket', 'vilka'],
        'WHO': ['vem', 'vilka', 'vems'],
        'WHERE': ['var', 'vart', 'varifrån'],
        'WHEN': ['när', 'vilken tid'],
        'WHY': ['varför', 'hur kommer det sig'],
        'HOW': ['hur', 'på vilket sätt'],
        'HOW_MANY': ['hur många', 'hur mycket'],
    }
    
    INTENT_PATTERNS = {
        'OFFICIAL': ['ansöka', 'ansökan', 'tillstånd', 'myndighet', 'riksdag', 'lag'],
        'NEWS': ['nyhet', 'aktuellt', 'senaste', 'idag', 'igår'],
        'GUIDE': ['hur man', 'guide', 'instruktion', 'steg för steg'],
        'DEFINITION': ['vad är', 'vad betyder', 'definition', 'förklaring'],
        'COMPARISON': ['skillnad mellan', 'jämförelse', 'kontra', 'vs'],
        'LOCAL': ['närmaste', 'i närheten', 'lokalt', 'här'],
    }
    
    def classify(self, query: str) -> Dict[str, str]:
        """Classify query type and intent"""
        query_lower = query.lower()
        
        result = {
            'question_type': 'STATEMENT',
            'intent': 'GENERAL',
            'is_question': False,
        }
        
        # Check question type
        for q_type, patterns in self.QUESTION_PATTERNS.items():
            for pattern in patterns:
                if query_lower.startswith(pattern) or f' {pattern} ' in query_lower:
                    result['question_type'] = q_type
                    result['is_question'] = True
                    break
        
        # Check intent
        for intent, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                if pattern in query_lower:
                    result['intent'] = intent
                    break
        
        return result


class SwedishNLPProcessor:
    """Main NLP processor for Swedish text"""
    
    def __init__(self):
        self.compound_splitter = SwedishCompoundSplitter()
        self.synonym_expander = SwedishSynonymExpander()
        self.question_classifier = SwedishQuestionClassifier()
        logger.info("Swedish NLP Processor initialized")
    
    def tokenize(self, text: str) -> List[str]:
        """Tokenize Swedish text into words"""
        # Normalize text
        text = text.lower()
        
        # Use regex to handle Swedish characters properly
        # Keep åäöÅÄÖ and hyphens within words
        tokens = re.findall(r'\b[\wåäöÅÄÖ]+(?:-[\wåäöÅÄÖ]+)*\b', text)
        
        return tokens
    
    def stem(self, word: str) -> str:
        """Stem a Swedish word"""
        return swedish_stemmer.stem(word.lower())
    
    def remove_stopwords(self, tokens: List[str]) -> List[str]:
        """Remove Swedish stopwords"""
        return [t for t in tokens if t.lower() not in SWEDISH_STOPWORDS]
    
    def filter_tokens(self, tokens: List[str]) -> List[str]:
        """Filter tokens by length and validity"""
        filtered = []
        for token in tokens:
            # Check length
            if len(token) < MIN_WORD_LENGTH or len(token) > MAX_WORD_LENGTH:
                continue
            # Check if contains at least one letter
            if not re.search(r'[a-zåäöÅÄÖ]', token):
                continue
            filtered.append(token)
        return filtered
    
    def extract_compounds(self, tokens: List[str]) -> List[str]:
        """Split compound words and return all components"""
        all_components = []
        for token in tokens:
            components = self.compound_splitter.split(token)
            all_components.extend(components)
        return all_components
    
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract named entities (basic pattern matching)"""
        entities = {
            'PERSON': [],
            'PLACE': [],
            'ORGANIZATION': [],
            'TIME': []
        }
        
        # Simple capitalization-based detection
        # In Swedish, proper nouns are capitalized
        words = text.split()
        for word in words:
            if word and word[0].isupper() and len(word) > 2:
                # This is a simplified approach
                # In production, use proper NER
                if any(suffix in word.lower() for suffix in ['sson', 'sen', 'berg', 'ström']):
                    entities['PERSON'].append(word)
                elif any(suffix in word.lower() for suffix in ['stad', 'borg', 'köping', 'by']):
                    entities['PLACE'].append(word)
                elif any(suffix in word.lower() for suffix in ['verket', 'myndigheten', 'styrelsen']):
                    entities['ORGANIZATION'].append(word)
        
        return entities
    
    def process(self, text: str) -> ProcessedText:
        """Full NLP processing pipeline"""
        # Tokenize
        tokens = self.tokenize(text)
        
        # Filter by length
        filtered = self.filter_tokens(tokens)
        
        # Remove stopwords
        no_stopwords = self.remove_stopwords(filtered)
        
        # Stem
        stems = [self.stem(t) for t in no_stopwords]
        
        # Split compounds
        compounds = self.extract_compounds(no_stopwords)
        
        # Extract entities
        entities = self.extract_entities(text)
        
        # Calculate term frequencies
        term_freq = Counter(stems)
        
        return ProcessedText(
            original=text,
            tokens=tokens,
            stems=stems,
            filtered_tokens=no_stopwords,
            compounds_split=compounds,
            entities=entities,
            term_frequencies=dict(term_freq)
        )
    
    @lru_cache(maxsize=10000)
    def _process_query_cached(self, query: str) -> Dict:
        """Cached query processing to speed up repeated searches"""
        # Basic processing
        processed = self.process(query)

        # Question classification
        classification = self.question_classifier.classify(query)

        # Synonym expansion for better recall
        expanded_terms = set()
        for term in processed.filtered_tokens:
            expanded_terms.update(self.synonym_expander.expand(term))

        return {
            'original_query': query,
            'tokens': tuple(processed.tokens),
            'filtered_tokens': tuple(processed.filtered_tokens),
            'stems': tuple(processed.stems),
            'compounds': tuple(processed.compounds_split),
            'expanded_terms': tuple(sorted(expanded_terms)),
            'question_type': classification['question_type'],
            'intent': classification['intent'],
            'is_question': classification['is_question'],
        }

    def process_query(self, query: str) -> Dict:
        """Process a search query with additional classification"""
        cached = self._process_query_cached(query)
        return {
            'original_query': cached['original_query'],
            'tokens': list(cached['tokens']),
            'filtered_tokens': list(cached['filtered_tokens']),
            'stems': list(cached['stems']),
            'compounds': list(cached['compounds']),
            'expanded_terms': list(cached['expanded_terms']),
            'question_type': cached['question_type'],
            'intent': cached['intent'],
            'is_question': cached['is_question'],
        }


# Create global processor instance
nlp_processor = SwedishNLPProcessor()


def main():
    """Test NLP processor"""
    # Test cases
    test_texts = [
        "Hur ansöker man om svenskt medborgarskap?",
        "riksdagsledamöter från miljöpartiet",
        "restauranger i Stockholm",
        "arbetstillstånd Sverige",
        "bästa universiteten i Sverige",
    ]
    
    logger.info("Testing Swedish NLP Processor")
    logger.info("=" * 80)
    
    for text in test_texts:
        logger.info(f"\nOriginal: {text}")
        result = nlp_processor.process_query(text)
        logger.info(f"Tokens: {result['tokens']}")
        logger.info(f"Filtered: {result['filtered_tokens']}")
        logger.info(f"Stems: {result['stems']}")
        logger.info(f"Compounds: {result['compounds']}")
        logger.info(f"Question type: {result['question_type']}")
        logger.info(f"Intent: {result['intent']}")
        logger.info("-" * 80)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
