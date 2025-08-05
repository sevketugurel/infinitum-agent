"""
Search Products Command - Handles product search requests
"""
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime

from ...core.value_objects.search_query import SearchQuery
from ...core.value_objects.user_preferences import UserPreferences


@dataclass
class SearchProductsCommand:
    """
    Command to search for products based on query and preferences.
    
    This represents a user's intent to search for products.
    """
    # Required fields
    query: SearchQuery
    
    # Optional context
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    user_preferences: Optional[UserPreferences] = None
    
    # Search parameters
    limit: int = 20
    offset: int = 0
    include_out_of_stock: bool = True
    
    # Filters
    category_filter: Optional[str] = None
    brand_filter: Optional[str] = None
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    rating_min: Optional[float] = None
    
    # Metadata
    timestamp: datetime = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    def __post_init__(self):
        """Set default timestamp if not provided"""
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
    
    @property
    def has_filters(self) -> bool:
        """Check if command has any filters applied"""
        return any([
            self.category_filter,
            self.brand_filter,
            self.price_min is not None,
            self.price_max is not None,
            self.rating_min is not None
        ])
    
    @property
    def is_authenticated(self) -> bool:
        """Check if search is from authenticated user"""
        return self.user_id is not None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert command to dictionary"""
        return {
            'query': self.query.to_dict(),
            'user_id': self.user_id,
            'session_id': self.session_id,
            'user_preferences': self.user_preferences.to_dict() if self.user_preferences else None,
            'search_parameters': {
                'limit': self.limit,
                'offset': self.offset,
                'include_out_of_stock': self.include_out_of_stock
            },
            'filters': {
                'category': self.category_filter,
                'brand': self.brand_filter,
                'price_min': self.price_min,
                'price_max': self.price_max,
                'rating_min': self.rating_min
            },
            'metadata': {
                'timestamp': self.timestamp.isoformat(),
                'ip_address': self.ip_address,
                'user_agent': self.user_agent,
                'has_filters': self.has_filters,
                'is_authenticated': self.is_authenticated
            }
        }


@dataclass
class SearchProductsResult:
    """
    Result of a product search command.
    
    Contains the search results and metadata about the search operation.
    """
    # Results
    products: List[Dict[str, Any]]
    total_count: int
    
    # Search metadata
    query_used: SearchQuery
    search_time_ms: int
    
    # Pagination
    limit: int
    offset: int
    has_more: bool
    
    # Analytics
    filters_applied: Dict[str, Any]
    results_source: str = "database"  # database, cache, external_api
    
    # Suggestions
    suggested_queries: List[str] = None
    related_categories: List[str] = None
    
    def __post_init__(self):
        """Set default values"""
        if self.suggested_queries is None:
            self.suggested_queries = []
        if self.related_categories is None:
            self.related_categories = []
    
    @property
    def result_count(self) -> int:
        """Get number of products returned"""
        return len(self.products)
    
    @property
    def has_results(self) -> bool:
        """Check if search returned any results"""
        return self.result_count > 0
    
    @property
    def is_partial_results(self) -> bool:
        """Check if results are partial (due to pagination)"""
        return self.total_count > (self.offset + self.result_count)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary"""
        return {
            'products': self.products,
            'total_count': self.total_count,
            'result_count': self.result_count,
            'query': self.query_used.to_dict(),
            'search_metadata': {
                'search_time_ms': self.search_time_ms,
                'results_source': self.results_source,
                'filters_applied': self.filters_applied
            },
            'pagination': {
                'limit': self.limit,
                'offset': self.offset,
                'has_more': self.has_more,
                'is_partial_results': self.is_partial_results
            },
            'suggestions': {
                'suggested_queries': self.suggested_queries,
                'related_categories': self.related_categories
            },
            'metadata': {
                'has_results': self.has_results,
                'timestamp': datetime.utcnow().isoformat()
            }
        }