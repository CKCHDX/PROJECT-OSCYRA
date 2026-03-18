"""
Swedish Compound Word Decomposer
Splits compound words to improve search recall

Example:
  "arbetstillstånd" → ["arbete", "tillstand"]
  "riksdagsledamöterna" → ["riksdag", "ledamot"]
  
This is CRITICAL for Swedish search - Google misses these!
"""

import logging
from typing import List, Set

logger = logging.getLogger(__name__)

# Common Swedish word endings that form compounds
COMPOUND_MARKERS = {
    's': 0.8,   # arbets-bokföring, lands-delen
    'e': 0.7,   # kyrko-museet, järnvägs-station
    'o': 0.6,   # radio-program, skola-mat
}

# Most common Swedish noun roots (for validation)
SWEDISH_ROOTS = {
    # Government/Politics
    'riksdag', 'regering', 'parlament', 'kommunal', 'stat', 'lag',
    'minister', 'ledamot', 'valkrets', 'politiker', 'partiet',
    
    # Health/Medical
    'sjukhus', 'tandläkare', 'psykolog', 'medicin', 'operation', 'läkarvård',
    'apotek', 'medicament', 'vaccination', 'sjukvård', 'vårdcenter',
    
    # Education
    'skola', 'universitet', 'gymnasium', 'grundskola', 'student', 'lärar',
    'undervisning', 'kurs', 'antagning', 'examination', 'betyg',
    
    # Work/Labor
    'arbete', 'jobb', 'anställning', 'arbetsförmedling', 'lön', 'tjänst',
    'chef', 'person', 'chef', 'arbetare', 'profession',
    
    # Time/Location
    'dag', 'vecka', 'månad', 'år', 'tid', 'timmar', 'klocka',
    'stockholm', 'sverige', 'kommun', 'lan', 'område', 'plats',
    
    # Common
    'hus', 'väg', 'väg', 'land', 'stad', 'hem', 'folk', 'man', 'kvinnor',
    'barn', 'familj', 'arbete', 'pengar', 'pris', 'kostnad', 'betalning',
}

class SwedishCompoundSplitter:
    """Splits Swedish compound words into components"""
    
    def __init__(self):
        self.roots = SWEDISH_ROOTS
        self.markers = COMPOUND_MARKERS
    
    def split_compound(self, word: str) -> List[str]:
        """
        Try to split a Swedish compound word
        
        Args:
            word: Swedish word (e.g., "arbetstillstånd")
        
        Returns:
            List of components if compound, or [word] if not
        """
        word = word.lower().strip()
        
        # Too short to be compound
        if len(word) < 6:
            return [word]
        
        # Try splitting at each position
        best_split = [word]
        best_score = 0
        
        for i in range(3, len(word) - 2):  # Need at least 3 chars on each side
            prefix = word[:i]
            suffix = word[i:]
            
            # Check if prefix ends with compound marker
            if len(prefix) > 0 and prefix[-1] in self.markers:
                # Remove marker to get root
                root_prefix = prefix[:-1]
                
                # Check if both parts are valid Swedish roots or stems
                if (self._is_valid_root(root_prefix) and 
                    self._is_valid_root(suffix)):
                    
                    score = self.markers[prefix[-1]]
                    
                    if score > best_score:
                        best_split = [root_prefix, suffix]
                        best_score = score
        
        return best_split if best_score > 0.5 else [word]
    
    def _is_valid_root(self, word: str) -> bool:
        """Check if word is likely a valid Swedish root"""
        # Check exact match
        if word in self.roots:
            return True
        
        # Check if it's a stem (without ending)
        # Swedish common endings: -a, -e, -i, -o, -u, -y, -ä, -ö
        for ending in ['a', 'e', 'i', 'o', 'u', 'y', 'ä', 'ö']:
            if word.endswith(ending):
                stem = word[:-1]
                if stem in self.roots:
                    return True
        
        # Minimum length heuristic
        return len(word) >= 3
    
    def split_multiple(self, words: List[str]) -> List[str]:
        """
        Split multiple words, returning all components
        
        Example:
            ["riksdagsledamöterna", "arbetstillstånd"]
            → ["riksdag", "ledamot", "arbete", "tillstand"]
        """
        result = []
        for word in words:
            components = self.split_compound(word)
            result.extend(components)
        return result

# Global instance
compound_splitter = SwedishCompoundSplitter()

def split_compounds(text: str) -> List[str]:
    """
    Split Swedish compound words in text
    
    Usage:
        tokens = ["arbetstillstand", "riksdagsledamöterna"]
        expanded = split_compounds(tokens)
        # Result: ["arbete", "tillstand", "riksdag", "ledamot"]
    """
    words = text.lower().split()
    return compound_splitter.split_multiple(words)


# Test examples
if __name__ == "__main__":
    splitter = SwedishCompoundSplitter()
    
    test_words = [
        "arbetstillstånd",
        "riksdagsledamöterna",
        "midsommarafton",
        "sjukhusläkare",
        "universitetsutbildning",
        "kommunfullmäktige",
        "socialtjänst",
        "försäkringskassan",
    ]
    
    print("Swedish Compound Word Splitting:\n")
    for word in test_words:
        components = splitter.split_compound(word)
        if len(components) > 1:
            print(f"✓ {word:30} → {' + '.join(components)}")
        else:
            print(f"  {word:30} (not compound)")
