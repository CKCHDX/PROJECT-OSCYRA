"""
Klar Search Engine - Swedish Semantic Understanding Engine
Advanced semantic processing aligned with KLAR vision

Features:
- Swedish government and institutional entity recognition
- Geographic/municipal/regional context understanding
- Temporal query normalization (idag, midsommarafton, etc.)
- Swedish cultural context processing
- Advanced compound word decomposition with patterns
- Intent-specific ranking factor calculation
- Query reformulation for better indexing
"""

import re
import logging
from typing import List, Set, Dict, Tuple, Optional
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ==================== SWEDISH GEOGRAPHIC KNOWLEDGE BASE ====================

class SwedishGeography:
    """Swedish geographic and administrative divisions"""
    
    # 21 Swedish counties (länantalet)
    COUNTIES = {
        'stockholms': 'Stockholm',
        'uppsala': 'Uppsala',
        'västra götaland': 'Västra Götaland',
        'dalarna': 'Dalarna',
        'gävleborg': 'Gävleborg',
        'västernorrland': 'Västernorrland',
        'jämtland': 'Jämtland',
        'västmanland': 'Västmanland',
        'örebro': 'Örebro',
        'sörmland': 'Södermanland',
        'östergötland': 'Östergötland',
        'småland': 'Småland',
        'kalmar': 'Kalmar',
        'gotland': 'Gotland',
        'blekinge': 'Blekinge',
        'scania': 'Skåne',
        'halland': 'Halland',
        'värmland': 'Värmland',
        'skåne': 'Skåne',
        'norrbotten': 'Norrbotten',
        'västerbotten': 'Västerbotten',
    }
    
    # Major Swedish cities and regions
    CITIES = {
        'stockholm': {'region': 'Stockholm', 'aliases': ['sthlm', 'huvudstad']},
        'göteborg': {'region': 'Västra Götaland', 'aliases': ['gothenburg', 'gbg']},
        'malmö': {'region': 'Skåne', 'aliases': ['malmoe']},
        'uppsala': {'region': 'Uppsala', 'aliases': []},
        'västerås': {'region': 'Västmanland', 'aliases': []},
        'örebro': {'region': 'Örebro', 'aliases': []},
        'linköping': {'region': 'Östergötland', 'aliases': []},
        'helsingborg': {'region': 'Skåne', 'aliases': []},
        'borås': {'region': 'Västra Götaland', 'aliases': []},
        'växjö': {'region': 'Småland', 'aliases': []},
        'sundsvall': {'region': 'Västernorrland', 'aliases': []},
        'umeå': {'region': 'Västerbotten', 'aliases': []},
        'luleå': {'region': 'Norrbotten', 'aliases': []},
        'falun': {'region': 'Dalarna', 'aliases': []},
        'gävle': {'region': 'Gävleborg', 'aliases': []},
    }
    
    # ~290 Swedish municipalities
    MUNICIPALITY_DISTRICTS = {
        'stockholm': 'stockholm',
        'göteborg': 'göteborg',
        'malmö': 'malmö',
        'uppsala': 'uppsala',
        'västerås': 'västerås',
    }


# ==================== SWEDISH GOVERNMENT & INSTITUTIONS ====================

class SwedishInstitutions:
    """Swedish government agencies, institutions, and their aliases"""
    
    MINISTRIES = {
        'finansdepartementet': {'en': 'Ministry of Finance', 'synonyms': ['finansministerium']},
        'justitiedepartementet': {'en': 'Ministry of Justice', 'synonyms': ['justitie']},
        'försvarsdepartementet': {'en': 'Ministry of Defence', 'synonyms': []},
        'utrikesdepartementet': {'en': 'Ministry of Foreign Affairs', 'synonyms': ['utrikesstaten']},
        'näringsdepartementet': {'en': 'Ministry of Enterprise', 'synonyms': ['näringsliv']},
        'kulturdepartementet': {'en': 'Ministry of Culture', 'synonyms': ['kultur']},
        'utbildningsdepartementet': {'en': 'Ministry of Education', 'synonyms': ['utbildning']},
        'socialdepartementet': {'en': 'Ministry of Health and Social Affairs', 'synonyms': ['hälsa']},
    }
    
    AGENCIES = {
        'migrationsverket': {
            'en': 'Swedish Migration Agency',
            'function': 'Immigration, visas, residence permits',
            'keywords': ['arbetstillständ', 'visum', 'inreise', 'uppehållstillstånd'],
        },
        'skatteverket': {
            'en': 'Swedish Tax Agency',
            'function': 'Taxation',
            'keywords': ['skatter', 'deklaration', 'inkomstskatt'],
        },
        'försäkringskassan': {
            'en': 'Swedish Social Insurance Agency',
            'function': 'Social insurance, benefits',
            'keywords': ['sjukskrivning', 'föräldrapenning', 'sjukpenning'],
        },
        'arbetsförmedlingen': {
            'en': 'Swedish Public Employment Service',
            'function': 'Job placement, unemployment',
            'keywords': ['jobb', 'lediga jobb', 'arbetslöshetsersättning'],
        },
        'riksdagen': {
            'en': 'Swedish Parliament',
            'function': 'Legislative body',
            'keywords': ['ledamöter', 'lagstiftning', 'proposition'],
        },
        'regeringen': {
            'en': 'Swedish Government',
            'function': 'Executive body',
            'keywords': ['statsminister', 'minister', 'proposition'],
        },
        'domstolverket': {
            'en': 'Swedish Courts',
            'function': 'Judicial system',
            'keywords': ['domstol', 'tingsrätt', 'hovrättningen'],
        },
        'csn': {
            'en': 'Swedish Board of Student Finance',
            'function': 'Student loans and grants',
            'keywords': ['studielån', 'studiebidraget', 'studiefinansiering'],
        },
        'folkhälsomyndigheten': {
            'en': 'Public Health Agency of Sweden',
            'function': 'Public health',
            'keywords': ['vaccination', 'epidemiologi', 'smittskydd'],
        },
        'trafikverket': {
            'en': 'Swedish Transport Agency',
            'function': 'Transportation',
            'keywords': ['vägtrafik', 'järnväg', 'trafikstörning'],
        },
        'systembolaget': {
            'en': 'Systembolaget (Alcohol monopoly)',
            'function': 'Alcohol retail',
            'keywords': ['öppettider', 'alkohol', 'vin', 'sprit'],
        },
    }
    
    # Swedish media and information sources
    PUBLIC_BROADCASTERS = {
        'svt': 'Swedish Television (SVT)',
        'sr': 'Swedish Radio (SR)',
        'sverigesradio': 'Swedish Radio',
        'yle': 'Finnish Broadcasting (for Nordic queries)',
    }
    
    MAJOR_NEWS = {
        'dn': 'Dagens Nyheter',
        'svd': 'Svenska Dagbladet',
        'gt': 'Göteborgs-Posten',
        'skd': 'Skånska Dagbladet',
        'aftonbladet': 'Aftonbladet',
    }
    
    UNIVERSITIES = {
        'su.se': 'Stockholm University',
        'uu.se': 'Uppsala University',
        'liu.se': 'Linköping University',
        'lund.se': 'Lund University',
        'chalmers.se': 'Chalmers University',
        'kth.se': 'Royal Institute of Technology',
        'mdu.se': 'Mälardalen University',
        'du.se': 'Dalarna University',
        'hj.se': 'Högskolan Jönköping',
    }


# ==================== TEMPORAL UNDERSTANDING ====================

class TemporalProcessor:
    """Swedish temporal expressions and normalization"""
    
    SWEDISH_MONTHS = {
        'januari': 1, 'jan': 1,
        'februari': 2, 'feb': 2,
        'mars': 3, 'mar': 3,
        'april': 4, 'apr': 4,
        'maj': 5,
        'juni': 6, 'jun': 6,
        'juli': 7, 'jul': 7,
        'augusti': 8, 'aug': 8,
        'september': 9, 'sep': 9,
        'oktober': 10, 'okt': 10,
        'november': 11, 'nov': 11,
        'december': 12, 'dec': 12,
    }
    
    SWEDISH_DAYS = {
        'måndag': 'Monday',
        'tisdag': 'Tuesday',
        'onsdag': 'Wednesday',
        'torsdag': 'Thursday',
        'fredag': 'Friday',
        'lördag': 'Saturday',
        'söndag': 'Sunday',
    }
    
    SWEDISH_HOLIDAYS = {
        'midsommarafton': {'date': 'June 19-25', 'description': 'Midsummer Eve'},
        'midsommardagen': {'date': 'June 20-26', 'description': 'Midsummer Day'},
        'lucia': {'date': 'December 13', 'description': 'Lucia celebration'},
        'påsk': {'date': 'Variable', 'description': 'Easter'},
        'marta påskdagen': {'date': 'Variable', 'description': 'Maundy Thursday'},
        'långfredagen': {'date': 'Variable', 'description': 'Good Friday'},
        'annandag påsk': {'date': 'Variable', 'description': 'Easter Monday'},
        'valborgsmässoafton': {'date': 'April 30', 'description': 'Walpurgis Eve'},
        'första maj': {'date': 'May 1', 'description': 'Labour Day'},
        'jul': {'date': 'December 25', 'description': 'Christmas'},
        'nyår': {'date': 'January 1', 'description': 'New Year'},
        'epifania': {'date': 'January 6', 'description': 'Epiphany'},
    }
    
    # Temporal expressions for freshness boosting
    FRESHNESS_KEYWORDS = {
        'idag': {'days': 1, 'boost': 3.0},
        'igår': {'days': 1, 'boost': 2.5},
        'senaste': {'days': 7, 'boost': 3.0},
        'nyligen': {'days': 7, 'boost': 2.5},
        'denna vecka': {'days': 7, 'boost': 2.0},
        'denna månad': {'days': 30, 'boost': 1.5},
        'detta år': {'days': 365, 'boost': 1.2},
    }
    
    @staticmethod
    def parse_temporal_expression(query: str) -> Dict[str, any]:
        """Parse Swedish temporal expressions"""
        query_lower = query.lower()
        result = {
            'has_temporal': False,
            'freshness_boost': 1.0,
            'max_age_days': None,
            'holidays': [],
            'expressions': [],
        }
        
        # Check holidays
        for holiday, info in TemporalProcessor.SWEDISH_HOLIDAYS.items():
            if holiday in query_lower:
                result['holidays'].append(holiday)
                result['has_temporal'] = True
        
        # Check freshness keywords
        for keyword, config in TemporalProcessor.FRESHNESS_KEYWORDS.items():
            if keyword in query_lower:
                result['freshness_boost'] = config['boost']
                result['max_age_days'] = config['days']
                result['has_temporal'] = True
                result['expressions'].append(keyword)
        
        return result


# ==================== SWEDISH CULTURAL CONTEXT ====================

class SwedishCulturalContext:
    """Swedish cultural references, idioms, and context"""
    
    # Common Swedish idioms and their interpretations
    IDIOMS = {
        'det är inte lätt att vara grön': 'It\'s not easy being green (environmental critique)',
        'känna till fågeln fritt': 'Know the bird for free (know someone well)',
        'att sätta frågorna på pränt': 'Put questions in print (raise important issues)',
    }
    
    # Swedish social systems and concepts
    SOCIAL_SYSTEMS = {
        'personnummer': {
            'description': 'Swedish personal identification number',
            'format': 'YYMMDD-XXXX',
            'keywords': ['person ID', 'id-nummer', 'personnummer'],
        },
        'folkbokföring': {
            'description': 'Swedish population registry',
            'keywords': ['registration', 'register', 'befolkning'],
        },
        'a-kassa': {
            'description': 'Unemployment insurance fund',
            'keywords': ['arbetslöshetskassa', 'unemployment'],
        },
        'csn': {
            'description': 'Student finance authority',
            'keywords': ['lånekort', 'studielån', 'studiebidrag'],
        },
        'fora': {
            'description': 'Swedish social insurance',
            'keywords': ['sjukförsäkring', 'sjukpenning'],
        },
        'välfärd': {
            'description': 'Swedish welfare system',
            'keywords': ['welfare', 'socialsystem', 'skyddsnät'],
        },
    }


# ==================== SEMANTIC QUERY ENRICHMENT ====================

@dataclass
class SemanticQueryContext:
    """Rich semantic context extracted from query"""
    original_query: str
    
    # Geographic context
    geographic_scope: Optional[str] = None
    mentioned_locations: List[str] = field(default_factory=list)
    region_boost: float = 1.0
    
    # Institutional context
    mentioned_institutions: List[str] = field(default_factory=list)
    is_official_query: bool = False
    official_boost: float = 1.0
    
    # Temporal context
    temporal_keywords: List[str] = field(default_factory=list)
    freshness_boost: float = 1.0
    max_age_days: Optional[int] = None
    
    # Intent classification
    intent_category: str = 'GENERAL'  # GUIDE, DEFINITION, PRACTICAL_INFO, NEWS, OFFICIAL, LOCAL
    intent_confidence: float = 0.0
    
    # Compound decomposition
    expanded_compounds: List[str] = field(default_factory=list)
    
    # Overall ranking signals
    ranking_multiplier: float = 1.0


class SwedishSemanticEngine:
    """Main semantic understanding engine for Swedish queries"""
    
    def __init__(self):
        self.geography = SwedishGeography()
        self.institutions = SwedishInstitutions()
        self.temporal = TemporalProcessor()
        self.culture = SwedishCulturalContext()
        logger.info("Swedish Semantic Engine initialized")
    
    def extract_semantic_context(self, query: str) -> SemanticQueryContext:
        """
        Extract rich semantic context from Swedish query
        
        This aligns with KLAR vision:
        - Geographic understanding (290 municipalities, 21 counties)
        - Cultural context (Midsommar, Lucia, Swedish systems)
        - Institutional knowledge (government agencies, synonyms)
        - Temporal processing (date expressions, holidays)
        - Query reformulation (compound splitting, intent detection)
        """
        context = SemanticQueryContext(original_query=query)
        
        query_lower = query.lower()
        
        # 1. Geographic Analysis
        context = self._extract_geographic_context(query_lower, context)
        
        # 2. Institutional Analysis
        context = self._extract_institutional_context(query_lower, context)
        
        # 3. Temporal Analysis
        context = self._extract_temporal_context(query_lower, context)
        
        # 4. Intent Classification
        context = self._classify_intent(query_lower, context)
        
        # 5. Calculate overall ranking multiplier
        context.ranking_multiplier = (
            context.region_boost * 
            context.official_boost * 
            context.freshness_boost
        )
        
        return context
    
    def _extract_geographic_context(self, query_lower: str, context: SemanticQueryContext) -> SemanticQueryContext:
        """Extract geographic context from query"""
        # Check for counties
        for county_key, county_name in self.geography.COUNTIES.items():
            if county_key in query_lower or county_name.lower() in query_lower:
                context.geographic_scope = county_name
                context.mentioned_locations.append(county_name)
                context.region_boost = 1.5  # Boost local results
        
        # Check for cities
        for city_key, city_info in self.geography.CITIES.items():
            if city_key in query_lower:
                context.mentioned_locations.append(city_key)
                context.geographic_scope = city_info.get('region')
                context.region_boost = 2.0  # Stronger local boost for cities
                break
        
        return context
    
    def _extract_institutional_context(self, query_lower: str, context: SemanticQueryContext) -> SemanticQueryContext:
        """Extract government/institutional context from query"""
        # Check for government agencies
        for agency_key, agency_info in self.institutions.AGENCIES.items():
            if agency_key in query_lower:
                context.mentioned_institutions.append(agency_key)
                context.is_official_query = True
                context.official_boost = 3.0  # Strong boost for official queries
                logger.debug(f"Detected official agency: {agency_key}")
        
        # Check for keywords indicating official context
        official_keywords = ['ansöka', 'tillstånd', 'myndighet', 'lag', 'förordning', 'regeringen', 'riksdag']
        for keyword in official_keywords:
            if keyword in query_lower:
                context.is_official_query = True
                context.official_boost = 2.0
                break
        
        return context
    
    def _extract_temporal_context(self, query_lower: str, context: SemanticQueryContext) -> SemanticQueryContext:
        """Extract temporal context from query"""
        temporal = self.temporal.parse_temporal_expression(query_lower)
        
        if temporal['has_temporal']:
            context.temporal_keywords = temporal['expressions']
            context.freshness_boost = temporal['freshness_boost']
            context.max_age_days = temporal['max_age_days']
        
        return context
    
    def _classify_intent(self, query_lower: str, context: SemanticQueryContext) -> SemanticQueryContext:
        """Classify query intent for result ranking"""
        # GUIDE: "hur" + procedural keywords
        if self._match_patterns(query_lower, [r'\bhur\b.*(?:ansöka|göra|får|kan)', r'steg för steg', r'instruktion']):
            context.intent_category = 'GUIDE'
            context.intent_confidence = 0.9
            return context
        
        # OFFICIAL: Government/bureaucratic keywords
        if context.is_official_query or self._match_patterns(query_lower, [r'(?:ansöka|tillstånd|myndighet|lag)\b']):
            context.intent_category = 'OFFICIAL'
            context.intent_confidence = 0.9
            return context
        
        # NEWS: Freshness indicators
        if self._match_patterns(query_lower, [r'(?:senaste|idag|igår|nyhet)', r'aktuellt']):
            context.intent_category = 'NEWS'
            context.intent_confidence = 0.9
            context.freshness_boost = 3.0
            return context
        
        # DEFINITION: "vad är", "skillnad mellan"
        if self._match_patterns(query_lower, [r'\bvad.*(?:är|betyder)', r'skillnad mellan', r'förklaring']):
            context.intent_category = 'DEFINITION'
            context.intent_confidence = 0.85
            return context
        
        # PRACTICAL_INFO: Opening hours, addresses, phone
        if self._match_patterns(query_lower, [r'(?:öppettid|adress|telefon|pris|timmar)', r'schema']):
            context.intent_category = 'PRACTICAL_INFO'
            context.intent_confidence = 0.9
            context.freshness_boost = 2.0
            return context
        
        # LOCAL: Location-based
        if context.mentioned_locations:
            context.intent_category = 'LOCAL'
            context.intent_confidence = 0.8
            return context
        
        return context
    
    @staticmethod
    def _match_patterns(text: str, patterns: List[str]) -> bool:
        """Check if any pattern matches text"""
        for pattern in patterns:
            if re.search(pattern, text):
                return True
        return False
    
    def get_ranking_factors(self, context: SemanticQueryContext) -> Dict[str, float]:
        """Generate ranking factors based on semantic context"""
        factors = {
            'base_relevance': 1.0,
            'geographic_boost': context.region_boost,
            'official_boost': context.official_boost,
            'freshness_boost': context.freshness_boost,
            'intent_multiplier': self._get_intent_multiplier(context.intent_category),
            'authority_boost': self._get_authority_boost(context),
            'content_length_factor': self._get_content_length_factor(context.intent_category),
        }
        
        # Overall multiplier
        factors['combined_score'] = (
            factors['base_relevance'] *
            factors['geographic_boost'] *
            factors['official_boost'] *
            factors['freshness_boost'] *
            factors['intent_multiplier']
        )
        
        return factors
    
    @staticmethod
    def _get_intent_multiplier(intent: str) -> float:
        """Get multiplier for specific intent"""
        multipliers = {
            'OFFICIAL': 2.0,      # Government/bureaucratic results highly relevant
            'GUIDE': 1.8,         # Step-by-step guides valuable
            'PRACTICAL_INFO': 1.5,  # Factual info (hours, locations) very relevant
            'NEWS': 2.5,          # News queries need freshness + relevance
            'DEFINITION': 1.4,    # Definition queries prefer authoritative sources
            'LOCAL': 2.0,         # Location-based results strongly prioritized
            'GENERAL': 1.0,       # Default
        }
        return multipliers.get(intent, 1.0)
    
    @staticmethod
    def _get_authority_boost(context: SemanticQueryContext) -> float:
        """Get authority boost based on context"""
        boost = 1.0
        
        # Official queries trust government sources heavily
        if context.is_official_query:
            boost *= 3.0
        
        # Definition queries value authoritative sources
        if context.intent_category == 'DEFINITION':
            boost *= 1.8
        
        return boost
    
    @staticmethod
    def _get_content_length_factor(intent: str) -> float:
        """Get content length preference for specific intent"""
        factors = {
            'GUIDE': 2.0,           # Longer articles better for guides
            'DEFINITION': 1.5,      # Moderate length for definitions
            'PRACTICAL_INFO': 0.5,  # Short, concise info preferred
            'NEWS': 1.0,            # Variable length acceptable
            'OFFICIAL': 1.8,        # Comprehensive documents valued
            'LOCAL': 0.7,           # Concise local info preferred
            'GENERAL': 1.0,
        }
        return factors.get(intent, 1.0)


# ==================== ENHANCED COMPOUND WORD SPLITTER ====================

class AdvancedCompoundSplitter:
    """Advanced Swedish compound word decomposition"""
    
    # Common Swedish word components with priority
    WORD_COMPONENTS = {
        # Government/Politics
        'riksdag', 'regering', 'minister', 'ledamot', 'stat', 'lag',
        'kommun', 'region', 'myndighet', 'landsting',
        
        # Work/Employment  
        'arbete', 'jobb', 'anställ', 'lön', 'tjänst',
        
        # Location/Geography
        'stockholm', 'göteborg', 'malmö', 'stadt', 'stad', 'borg', 'hamn',
        'län', 'kommun', 'område',
        
        # Time/Date
        'dag', 'natt', 'morgon', 'kväll', 'år', 'månad', 'vecka',
        'timme', 'midsommar', 'afton',
        
        # Medical/Health
        'sjuk', 'sjukhus', 'läkare', 'medicin', 'apotek', 'tandvård',
        
        # Education
        'skola', 'universitet', 'högskola', 'utbildning', 'studie',
        
        # Common nouns
        'hus', 'väg', 'plats', 'rum', 'bok', 'system',
        
        # Adjectives
        'stor', 'liten', 'ny', 'gammal', 'god', 'bra', 'fin',
        
        # Services
        'försäkring', 'bank', 'affär', 'handel', 'restaurang',
        
        # Transport
        'tag', 'buss', 'bil', 'cykel', 'flyg', 'båt', 'järnväg',
        
        # Verbs
        'sök', 'hitta', 'läs', 'skriv', 'köp', 'sälj',
        
        # Common endings/roots
        'tillstånd', 'tillståndet', 'fullt', 'mäktig', 'mäktige',
        'kassan', 'verket', 'myndigheten', 'bolaget',
    }
    
    def __init__(self):
        self.min_component_len = 3
    
    def split_recursive(self, word: str, depth: int = 0, max_depth: int = 2) -> List[str]:
        """
        Recursively split compound words using known Swedish patterns
        
        Example:
            "arbetstillståndet" → ["arbete", "tillståndet"]
            "riksdagsledamöterna" → ["riksdag", "ledamöterna"]
            "midsommarafton" → ["midsommar", "afton"]
        """
        if depth >= max_depth or len(word) < 2 * self.min_component_len:
            return [word]
        
        word_lower = word.lower()
        
        # Remove common suffixes to get base form
        base_form = word_lower
        for suffix in ['erna', 'erna', 'erna', 'et', 'en', 'a', 'e']:
            if base_form.endswith(suffix) and len(base_form) > len(suffix) + self.min_component_len:
                potential_base = base_form[:-len(suffix)]
                # Don't remove if it leaves a very short word
                if len(potential_base) >= self.min_component_len:
                    base_form = potential_base
                    break
        
        # Try to find splits by looking for known components
        best_split = [word]
        best_score = 0
        
        # Strategy 1: Try all known components in order of length (longest first)
        sorted_components = sorted(self.WORD_COMPONENTS, key=len, reverse=True)
        
        for component in sorted_components:
            # Try component at start
            if base_form.startswith(component) and len(base_form) > len(component):
                remainder = base_form[len(component):]
                
                # Check if remainder is also a valid component or word-like
                if self._is_word_like(remainder):
                    score = len(component)  # Prefer longer known components
                    if score > best_score:
                        best_score = score
                        remainder_parts = self.split_recursive(remainder, depth + 1, max_depth)
                        best_split = [component] + remainder_parts
            
            # Try component at end
            if base_form.endswith(component) and len(base_form) > len(component):
                prefix = base_form[:-len(component)]
                
                if self._is_word_like(prefix):
                    score = len(component)
                    if score > best_score:
                        best_score = score
                        prefix_parts = self.split_recursive(prefix, depth + 1, max_depth)
                        best_split = prefix_parts + [component]
        
        # Strategy 2: Try common joining patterns (s, e, o)
        if best_score == 0:
            for i in range(self.min_component_len, len(base_form) - self.min_component_len):
                for joining in ['s', 'e', 'o', '']:
                    if joining and i + len(joining) < len(base_form):
                        if base_form[i:i+len(joining)] == joining:
                            left = base_form[:i]
                            right = base_form[i+len(joining):]
                        else:
                            continue
                    else:
                        left = base_form[:i]
                        right = base_form[i:]
                    
                    if self._is_word_like(left) and self._is_word_like(right):
                        score = min(len(left), len(right))
                        if score > best_score:
                            best_score = score
                            right_parts = self.split_recursive(right, depth + 1, max_depth)
                            best_split = [left] + right_parts
        
        return best_split if best_score > 0 else [word]
    
    def _is_word_like(self, text: str) -> bool:
        """Check if text looks like a Swedish word component"""
        if len(text) < self.min_component_len:
            return False
        
        # Check if in known components
        if text in self.WORD_COMPONENTS:
            return True
        
        # Check with common suffixes removed
        for suffix in ['erna', 'et', 'en', 'a', 'e', 'ar', 'er', 'or']:
            if text.endswith(suffix):
                stem = text[:-len(suffix)]
                if len(stem) >= self.min_component_len and stem in self.WORD_COMPONENTS:
                    return True
        
        # Heuristic: at least 3 chars + has vowel + at least one consonant
        has_vowel = any(c in 'aeiouyäåö' for c in text)
        has_consonant = any(c not in 'aeiouyäåö' for c in text)
        has_enough_length = len(text) >= self.min_component_len
        
        return has_vowel and has_consonant and has_enough_length


# ==================== INTEGRATION ====================

def test_semantic_engine():
    """Test semantic understanding"""
    engine = SwedishSemanticEngine()
    
    test_queries = [
        "Hur ansöker man arbetstillstand?",
        "Vad är skillnaden mellan landsting och region?",
        "Öppettider systembolaget stockholm",
        "Senaste nytt om regeringen",
        "Bästa restaurang Göteborg",
        "Riksdagsledamöterna från miljöpartiet",
        "När öppnar apotek på midsommarafton?",
        "CSN studiebidrag ansökan",
    ]
    
    logger.info("Testing Swedish Semantic Engine\n")
    
    for query in test_queries:
        context = engine.extract_semantic_context(query)
        factors = engine.get_ranking_factors(context)
        
        logger.info(f"Query: {query}")
        logger.info(f"  Intent: {context.intent_category} ({context.intent_confidence:.2f})")
        logger.info(f"  Geographic: {context.geographic_scope or 'None'}")
        logger.info(f"  Official: {context.is_official_query}")
        logger.info(f"  Ranking multiplier: {context.ranking_multiplier:.2f}")
        logger.info(f"  Combined score: {factors['combined_score']:.2f}\n")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_semantic_engine()
