"""
SearchQuery value object - Represents user search queries with metadata
"""
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Set
from datetime import datetime
import re
from enum import Enum


class SearchType(Enum):
    """Types of search queries"""
    PRODUCT = "product"
    CATEGORY = "category"
    BRAND = "brand"
    FEATURE = "feature"
    PRICE_RANGE = "price_range"
    COMPARISON = "comparison"
    GENERAL = "general"


class SearchIntent(Enum):
    """User intent behind the search"""
    BROWSE = "browse"  # Just looking around
    RESEARCH = "research"  # Gathering information
    COMPARE = "compare"  # Comparing options
    BUY = "buy"  # Ready to purchase
    SUPPORT = "support"  # Looking for help/support


@dataclass(frozen=True)
class SearchQuery:
    """
    SearchQuery value object that encapsulates user search queries with metadata.
    
    This is immutable (frozen=True) as value objects should be.
    """
    query: str
    search_type: SearchType = SearchType.GENERAL
    search_intent: SearchIntent = SearchIntent.BROWSE
    filters: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate search query data after initialization"""
        if not self.query or not self.query.strip():
            raise ValueError("Search query cannot be empty")
        
        if len(self.query.strip()) > 500:
            raise ValueError("Search query cannot exceed 500 characters")
        
        # Set default timestamp if not provided
        if self.timestamp is None:
            object.__setattr__(self, 'timestamp', datetime.utcnow())
        
        # Set default filters if not provided
        if self.filters is None:
            object.__setattr__(self, 'filters', {})
    
    @property
    def normalized_query(self) -> str:
        """Get normalized version of the query"""
        return self.query.strip().lower()
    
    @property
    def word_count(self) -> int:
        """Get number of words in the query"""
        return len(self.query.strip().split())
    
    @property
    def is_short_query(self) -> bool:
        """Check if query is short (1-2 words)"""
        return self.word_count <= 2
    
    @property
    def is_long_query(self) -> bool:
        """Check if query is long (5+ words)"""
        return self.word_count >= 5
    
    @property
    def contains_brand(self) -> bool:
        """Check if query likely contains a brand name"""
        # Common brand indicators
        brand_patterns = [
            r'\b(apple|samsung|google|microsoft|amazon|nike|adidas)\b',
            r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b',  # CamelCase patterns
        ]
        
        for pattern in brand_patterns:
            if re.search(pattern, self.query, re.IGNORECASE):
                return True
        return False
    
    @property
    def contains_price(self) -> bool:
        """Check if query contains price-related terms"""
        price_patterns = [
            r'\$\d+',  # $100
            r'\d+\s*(dollars?|usd|eur|gbp)',  # 100 dollars
            r'(under|below|less than|cheaper than)\s*\$?\d+',
            r'(over|above|more than|expensive)\s*\$?\d+',
            r'(budget|cheap|affordable|expensive|premium)',
            r'price\s*(range|between)',
        ]
        
        for pattern in price_patterns:
            if re.search(pattern, self.query, re.IGNORECASE):
                return True
        return False
    
    @property
    def contains_comparison(self) -> bool:
        """Check if query is asking for comparison"""
        comparison_terms = [
            'vs', 'versus', 'compare', 'comparison', 'difference',
            'better', 'best', 'which', 'or', 'alternative'
        ]
        
        query_lower = self.normalized_query
        return any(term in query_lower for term in comparison_terms)
    
    def extract_keywords(self) -> List[str]:
        """Extract meaningful keywords from the query"""
        # Remove common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these',
            'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him',
            'her', 'us', 'them', 'my', 'your', 'his', 'her', 'its', 'our', 'their'
        }
        
        # Extract words and filter out stop words
        words = re.findall(r'\b[a-zA-Z]+\b', self.normalized_query)
        keywords = [word for word in words if word not in stop_words and len(word) > 2]
        
        return keywords
    
    def get_search_suggestions(self) -> List[str]:
        """Generate search suggestions based on the query"""
        suggestions = []
        keywords = self.extract_keywords()
        
        if self.contains_brand:
            suggestions.append(f"{self.query} reviews")
            suggestions.append(f"{self.query} price")
        
        if self.contains_comparison:
            suggestions.append(f"{self.query} pros and cons")
            suggestions.append(f"{self.query} features")
        
        if len(keywords) > 0:
            main_keyword = keywords[0]
            suggestions.extend([
                f"best {main_keyword}",
                f"{main_keyword} reviews",
                f"cheap {main_keyword}",
                f"{main_keyword} alternatives"
            ])
        
        return suggestions[:5]  # Limit to 5 suggestions
    
    def infer_search_type(self) -> SearchType:
        """Infer the search type based on query content"""
        query_lower = self.normalized_query
        
        if self.contains_comparison:
            return SearchType.COMPARISON
        elif self.contains_price:
            return SearchType.PRICE_RANGE
        elif self.contains_brand:
            return SearchType.BRAND
        elif any(word in query_lower for word in ['category', 'type', 'kind']):
            return SearchType.CATEGORY
        elif any(word in query_lower for word in ['feature', 'specification', 'spec']):
            return SearchType.FEATURE
        else:
            return SearchType.PRODUCT
    
    def infer_search_intent(self) -> SearchIntent:
        """Infer the search intent based on query content"""
        query_lower = self.normalized_query
        
        # Buy intent indicators
        buy_indicators = ['buy', 'purchase', 'order', 'shop', 'store', 'price', 'deal']
        if any(indicator in query_lower for indicator in buy_indicators):
            return SearchIntent.BUY
        
        # Compare intent indicators
        compare_indicators = ['compare', 'vs', 'versus', 'difference', 'better', 'best']
        if any(indicator in query_lower for indicator in compare_indicators):
            return SearchIntent.COMPARE
        
        # Research intent indicators
        research_indicators = ['review', 'specification', 'feature', 'how', 'what', 'why']
        if any(indicator in query_lower for indicator in research_indicators):
            return SearchIntent.RESEARCH
        
        # Support intent indicators
        support_indicators = ['help', 'support', 'problem', 'issue', 'fix', 'troubleshoot']
        if any(indicator in query_lower for indicator in support_indicators):
            return SearchIntent.SUPPORT
        
        return SearchIntent.BROWSE
    
    def get_complexity_score(self) -> float:
        """Get complexity score of the query (0.0 to 1.0)"""
        score = 0.0
        
        # Word count factor
        if self.word_count <= 2:
            score += 0.1
        elif self.word_count <= 4:
            score += 0.3
        elif self.word_count <= 6:
            score += 0.5
        else:
            score += 0.7
        
        # Special patterns
        if self.contains_comparison:
            score += 0.2
        if self.contains_price:
            score += 0.1
        if self.contains_brand:
            score += 0.1
        
        return min(score, 1.0)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            'query': self.query,
            'normalized_query': self.normalized_query,
            'search_type': self.search_type.value,
            'search_intent': self.search_intent.value,
            'filters': self.filters,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'metadata': {
                'word_count': self.word_count,
                'is_short_query': self.is_short_query,
                'is_long_query': self.is_long_query,
                'contains_brand': self.contains_brand,
                'contains_price': self.contains_price,
                'contains_comparison': self.contains_comparison,
                'keywords': self.extract_keywords(),
                'complexity_score': self.get_complexity_score(),
                'suggestions': self.get_search_suggestions()
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SearchQuery':
        """Create SearchQuery from dictionary"""
        timestamp = None
        if data.get('timestamp'):
            timestamp = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
        
        return cls(
            query=data['query'],
            search_type=SearchType(data.get('search_type', 'general')),
            search_intent=SearchIntent(data.get('search_intent', 'browse')),
            filters=data.get('filters'),
            timestamp=timestamp
        )
    
    @classmethod
    def create_smart(cls, query: str, **kwargs) -> 'SearchQuery':
        """
        Create SearchQuery with automatic type and intent inference
        """
        temp_query = cls(query=query)
        
        return cls(
            query=query,
            search_type=kwargs.get('search_type', temp_query.infer_search_type()),
            search_intent=kwargs.get('search_intent', temp_query.infer_search_intent()),
            filters=kwargs.get('filters'),
            timestamp=kwargs.get('timestamp')
        )
    
    def __str__(self) -> str:
        """String representation"""
        return f"SearchQuery('{self.query}', {self.search_type.value}, {self.search_intent.value})"
    
    def __len__(self) -> int:
        """Length of the query"""
        return len(self.query)