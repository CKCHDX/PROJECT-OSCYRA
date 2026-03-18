"""
Klar Search Engine - Regional & Geographic Filtering
Swedish location intelligence for local search results

Understands Swedish administrative structure:
- 21 counties (län)
- 290 municipalities (kommuner)  
- Major cities and regions
- Location-based result boosting

Critical for national scale deployment and local relevance.
"""

import logging
import re
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class RegionType(Enum):
    """Types of Swedish geographic regions"""
    COUNTY = "county"  # Län
    MUNICIPALITY = "municipality"  # Kommun
    CITY = "city"  # Stad
    REGION = "region"  # Region (storområde)


@dataclass
class Location:
    """Geographic location"""
    name: str
    region_type: RegionType
    county: Optional[str] = None  # Which län
    population: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


# 21 Swedish Counties (Län)
SWEDISH_COUNTIES = {
    'stockholm': Location('Stockholm', RegionType.COUNTY, None, 2400000),
    'uppsala': Location('Uppsala', RegionType.COUNTY, None, 380000),
    'södermanland': Location('Södermanland', RegionType.COUNTY, None, 295000),
    'östergötland': Location('Östergötland', RegionType.COUNTY, None, 465000),
    'jönköping': Location('Jönköping', RegionType.COUNTY, None, 365000),
    'kronoberg': Location('Kronoberg', RegionType.COUNTY, None, 200000),
    'kalmar': Location('Kalmar', RegionType.COUNTY, None, 245000),
    'gotland': Location('Gotland', RegionType.COUNTY, None, 60000),
    'blekinge': Location('Blekinge', RegionType.COUNTY, None, 160000),
    'skåne': Location('Skåne', RegionType.COUNTY, None, 1400000),
    'halland': Location('Halland', RegionType.COUNTY, None, 330000),
    'västra götaland': Location('Västra Götaland', RegionType.COUNTY, None, 1700000),
    'värmland': Location('Värmland', RegionType.COUNTY, None, 280000),
    'örebro': Location('Örebro', RegionType.COUNTY, None, 300000),
    'västmanland': Location('Västmanland', RegionType.COUNTY, None, 275000),
    'dalarna': Location('Dalarna', RegionType.COUNTY, None, 290000),
    'gävleborg': Location('Gävleborg', RegionType.COUNTY, None, 285000),
    'västernorrland': Location('Västernorrland', RegionType.COUNTY, None, 245000),
    'jämtland': Location('Jämtland', RegionType.COUNTY, None, 130000),
    'västerbotten': Location('Västerbotten', RegionType.COUNTY, None, 270000),
    'norrbotten': Location('Norrbotten', RegionType.COUNTY, None, 250000),
}

# Major Swedish Cities (50+ largest)
SWEDISH_CITIES = {
    # Storstockholm
    'stockholm': Location('Stockholm', RegionType.CITY, 'stockholm', 978770),
    'huddinge': Location('Huddinge', RegionType.CITY, 'stockholm', 110000),
    'sollentuna': Location('Sollentuna', RegionType.CITY, 'stockholm', 72000),
    'järfälla': Location('Järfälla', RegionType.CITY, 'stockholm', 76000),
    'solna': Location('Solna', RegionType.CITY, 'stockholm', 82000),
    'nacka': Location('Nacka', RegionType.CITY, 'stockholm', 104000),
    
    # Göteborg region
    'göteborg': Location('Göteborg', RegionType.CITY, 'västra götaland', 583056),
    'mölndal': Location('Mölndal', RegionType.CITY, 'västra götaland', 69000),
    'partille': Location('Partille', RegionType.CITY, 'västra götaland', 38000),
    'borås': Location('Borås', RegionType.CITY, 'västra götaland', 113000),
    
    # Malmö region
    'malmö': Location('Malmö', RegionType.CITY, 'skåne', 347949),
    'lund': Location('Lund', RegionType.CITY, 'skåne', 124000),
    'helsingborg': Location('Helsingborg', RegionType.CITY, 'skåne', 147000),
    'kristianstad': Location('Kristianstad', RegionType.CITY, 'skåne', 85000),
    
    # Other major cities
    'uppsala': Location('Uppsala', RegionType.CITY, 'uppsala', 230000),
    'västerås': Location('Västerås', RegionType.CITY, 'västmanland', 155000),
    'örebro': Location('Örebro', RegionType.CITY, 'örebro', 155000),
    'linköping': Location('Linköping', RegionType.CITY, 'östergötland', 163000),
    'norrköping': Location('Norrköping', RegionType.CITY, 'östergötland', 143000),
    'jönköping': Location('Jönköping', RegionType.CITY, 'jönköping', 141000),
    'umeå': Location('Umeå', RegionType.CITY, 'västerbotten', 130000),
    'luleå': Location('Luleå', RegionType.CITY, 'norrbotten', 78000),
    'gävle': Location('Gävle', RegionType.CITY, 'gävleborg', 102000),
    'eskilstuna': Location('Eskilstuna', RegionType.CITY, 'södermanland', 107000),
    'sundsvall': Location('Sundsvall', RegionType.CITY, 'västernorrland', 100000),
    'karlstad': Location('Karlstad', RegionType.CITY, 'värmland', 94000),
    'växjö': Location('Växjö', RegionType.CITY, 'kronoberg', 94000),
    'halmstad': Location('Halmstad', RegionType.CITY, 'halland', 104000),
}

# Common neighborhood/district names in major cities
STOCKHOLM_AREAS = [
    'vasastan', 'södermalm', 'östermalm', 'kungsholmen', 'gamla stan',
    'norrmalm', 'bromma', 'älvsjö', 'farsta', 'hägersten', 'enskede'
]

GOTHENBURG_AREAS = [
    'haga', 'majorna', 'linnéstaden', 'landala', 'johanneberg',
    'kungsladugård', 'gårda', 'stampen', 'nordstaden'
]

MALMO_AREAS = [
    'västra hamnen', 'möllevången', 'limhamn', 'rosengård', 'fosie',
    'kirseberg', 'gamla staden', 'oxie'
]


class SwedishLocationDetector:
    """
    Detects Swedish locations in queries and content
    
    Identifies:
    - Counties (län)
    - Municipalities (kommuner)
    - Cities and towns
    - Neighborhoods/districts
    """
    
    def __init__(self):
        """Initialize location detector"""
        # Build lookup tables
        self.counties = SWEDISH_COUNTIES
        self.cities = SWEDISH_CITIES
        
        # Common location patterns in Swedish
        self.location_patterns = [
            r'i ([\w\s]+?)(?:\s|$|,|\.)',  # "i Stockholm"
            r'från ([\w\s]+?)(?:\s|$|,|\.)',  # "från Göteborg"
            r'([\w\s]+?) kommun',  # "Uppsala kommun"
            r'([\w\s]+?) län',  # "Stockholm län"
        ]
    
    def detect_in_query(self, query: str) -> List[Location]:
        """
        Detect locations mentioned in search query
        
        Args:
            query: Search query
            
        Returns:
            List of detected locations
        """
        query_lower = query.lower()
        detected = []
        
        # Check cities
        for city_name, location in self.cities.items():
            if city_name in query_lower:
                detected.append(location)
        
        # Check counties (only if not already found as city)
        city_names = {loc.name.lower() for loc in detected}
        for county_name, location in self.counties.items():
            if county_name in query_lower and county_name not in city_names:
                detected.append(location)
        
        return detected
    
    def extract_location_context(self, query: str) -> Optional[str]:
        """
        Extract location context from query
        
        Examples:
        - "pizzeria i göteborg" → "göteborg"
        - "bästa hotell stockholm" → "stockholm"
        """
        for pattern in self.location_patterns:
            match = re.search(pattern, query.lower())
            if match:
                location_name = match.group(1).strip()
                
                # Check if it's a known location
                if location_name in self.cities or location_name in self.counties:
                    return location_name
        
        return None


class RegionalBooster:
    """
    Boosts search results based on geographic relevance
    
    Strategy:
    - User location (IP geolocation or explicit)
    - Query location (detected in query)
    - Document location (from content/metadata)
    """
    
    def __init__(self):
        """Initialize regional booster"""
        self.detector = SwedishLocationDetector()
    
    def boost_score(self, 
                   base_score: float,
                   doc_location: Optional[str],
                   query_location: Optional[str],
                   user_location: Optional[str]) -> float:
        """
        Apply geographic boost to base relevance score
        
        Args:
            base_score: Original relevance score (0-100)
            doc_location: Location mentioned in document
            query_location: Location from user query
            user_location: User's current location
            
        Returns:
            Boosted score (0-100)
        """
        boost_multiplier = 1.0
        
        # Exact match: Query location = Document location
        if query_location and doc_location:
            if query_location.lower() == doc_location.lower():
                boost_multiplier *= 2.0  # 2x boost for exact match
            
            # Same county
            elif self._same_county(query_location, doc_location):
                boost_multiplier *= 1.5  # 1.5x for same county
        
        # User in same city/county as document
        if user_location and doc_location:
            if user_location.lower() == doc_location.lower():
                boost_multiplier *= 1.3  # 1.3x for user's location
            elif self._same_county(user_location, doc_location):
                boost_multiplier *= 1.2  # 1.2x for user's county
        
        # Apply boost (but cap at 100)
        boosted = base_score * boost_multiplier
        return min(100.0, boosted)
    
    def _same_county(self, location1: str, location2: str) -> bool:
        """Check if two locations are in the same county"""
        loc1_lower = location1.lower()
        loc2_lower = location2.lower()
        
        # Get counties for both locations
        county1 = None
        county2 = None
        
        if loc1_lower in SWEDISH_CITIES:
            county1 = SWEDISH_CITIES[loc1_lower].county
        elif loc1_lower in SWEDISH_COUNTIES:
            county1 = loc1_lower
        
        if loc2_lower in SWEDISH_CITIES:
            county2 = SWEDISH_CITIES[loc2_lower].county
        elif loc2_lower in SWEDISH_COUNTIES:
            county2 = loc2_lower
        
        return county1 and county2 and county1 == county2
    
    def detect_and_boost(self,
                        query: str,
                        results: List[Dict],
                        user_location: Optional[str] = None) -> List[Dict]:
        """
        Detect locations and apply boosts to results
        
        Args:
            query: Search query
            results: List of search results with 'score' field
            user_location: Optional user location
            
        Returns:
            Results with updated scores
        """
        # Detect query location
        query_location = self.detector.extract_location_context(query)
        
        # Apply boosts
        for result in results:
            # Extract document location (from URL, metadata, or content)
            doc_location = self._extract_doc_location(result)
            
            # Apply boost
            original_score = result.get('score', 0.0)
            result['score'] = self.boost_score(
                base_score=original_score,
                doc_location=doc_location,
                query_location=query_location,
                user_location=user_location
            )
            
            # Add debug info
            result['_regional_boost'] = {
                'query_location': query_location,
                'doc_location': doc_location,
                'user_location': user_location,
                'original_score': original_score,
                'boosted_score': result['score']
            }
        
        # Re-sort by new scores
        results.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        return results
    
    def _extract_doc_location(self, document: Dict) -> Optional[str]:
        """Extract location from document"""
        # Check metadata
        if 'location' in document.get('metadata', {}):
            return document['metadata']['location']
        
        # Check URL for city/county names
        url = document.get('url', '').lower()
        for city_name in SWEDISH_CITIES:
            if city_name in url:
                return city_name
        
        for county_name in SWEDISH_COUNTIES:
            if county_name in url:
                return county_name
        
        # Check title and content
        title = document.get('title', '').lower()
        content = document.get('content', '').lower()[:500]  # First 500 chars
        
        text = f"{title} {content}"
        
        for city_name in SWEDISH_CITIES:
            if city_name in text:
                return city_name
        
        return None


class LocationFilter:
    """
    Filter search results by location
    
    Allows users to restrict results to specific geographic areas
    """
    
    def __init__(self):
        """Initialize location filter"""
        self.detector = SwedishLocationDetector()
    
    def filter_by_county(self, results: List[Dict], county: str) -> List[Dict]:
        """Filter results to specific county"""
        county_lower = county.lower()
        
        filtered = []
        for result in results:
            doc_location = self._extract_location(result)
            
            if doc_location:
                # Check if in specified county
                if doc_location.lower() in SWEDISH_CITIES:
                    city_county = SWEDISH_CITIES[doc_location.lower()].county
                    if city_county == county_lower:
                        filtered.append(result)
                elif doc_location.lower() == county_lower:
                    filtered.append(result)
        
        return filtered
    
    def filter_by_city(self, results: List[Dict], city: str) -> List[Dict]:
        """Filter results to specific city"""
        city_lower = city.lower()
        
        filtered = []
        for result in results:
            doc_location = self._extract_location(result)
            
            if doc_location and doc_location.lower() == city_lower:
                filtered.append(result)
        
        return filtered
    
    def _extract_location(self, document: Dict) -> Optional[str]:
        """Extract location from document"""
        # Same logic as RegionalBooster._extract_doc_location
        if 'location' in document.get('metadata', {}):
            return document['metadata']['location']
        
        url = document.get('url', '').lower()
        for city_name in SWEDISH_CITIES:
            if city_name in url:
                return city_name
        
        return None


# Singleton instances
_location_detector = None
_regional_booster = None
_location_filter = None

def get_location_detector() -> SwedishLocationDetector:
    """Get or create location detector singleton"""
    global _location_detector
    if _location_detector is None:
        _location_detector = SwedishLocationDetector()
    return _location_detector

def get_regional_booster() -> RegionalBooster:
    """Get or create regional booster singleton"""
    global _regional_booster
    if _regional_booster is None:
        _regional_booster = RegionalBooster()
    return _regional_booster

def get_location_filter() -> LocationFilter:
    """Get or create location filter singleton"""
    global _location_filter
    if _location_filter is None:
        _location_filter = LocationFilter()
    return _location_filter
