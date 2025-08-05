"""
Get Product Query - Handles product detail retrieval requests
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from datetime import datetime


@dataclass
class GetProductQuery:
    """
    Query to get detailed information about a specific product.
    
    This represents a request to retrieve product details.
    """
    # Required fields
    product_id: str
    
    # Optional context
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    
    # Options
    include_reviews: bool = True
    include_related_products: bool = True
    include_price_history: bool = False
    
    # Metadata
    timestamp: datetime = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    def __post_init__(self):
        """Set default timestamp if not provided"""
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
    
    @property
    def is_authenticated(self) -> bool:
        """Check if query is from authenticated user"""
        return self.user_id is not None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert query to dictionary"""
        return {
            'product_id': self.product_id,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'options': {
                'include_reviews': self.include_reviews,
                'include_related_products': self.include_related_products,
                'include_price_history': self.include_price_history
            },
            'metadata': {
                'timestamp': self.timestamp.isoformat(),
                'ip_address': self.ip_address,
                'user_agent': self.user_agent,
                'is_authenticated': self.is_authenticated
            }
        }


@dataclass
class GetProductResult:
    """
    Result of a get product query.
    
    Contains the product details and related information.
    """
    # Core product data
    product: Optional[Dict[str, Any]]
    
    # Additional data
    reviews: Optional[List[Dict[str, Any]]] = None
    related_products: Optional[List[Dict[str, Any]]] = None
    price_history: Optional[List[Dict[str, Any]]] = None
    
    # Metadata
    found: bool = True
    retrieval_time_ms: int = 0
    data_source: str = "database"  # database, cache, external_api
    
    # User-specific data
    user_has_bookmarked: bool = False
    user_rating: Optional[float] = None
    
    def __post_init__(self):
        """Set found status based on product presence"""
        self.found = self.product is not None
    
    @property
    def has_reviews(self) -> bool:
        """Check if product has reviews"""
        return self.reviews is not None and len(self.reviews) > 0
    
    @property
    def has_related_products(self) -> bool:
        """Check if related products are available"""
        return self.related_products is not None and len(self.related_products) > 0
    
    @property
    def has_price_history(self) -> bool:
        """Check if price history is available"""
        return self.price_history is not None and len(self.price_history) > 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary"""
        return {
            'product': self.product,
            'reviews': self.reviews,
            'related_products': self.related_products,
            'price_history': self.price_history,
            'metadata': {
                'found': self.found,
                'retrieval_time_ms': self.retrieval_time_ms,
                'data_source': self.data_source,
                'has_reviews': self.has_reviews,
                'has_related_products': self.has_related_products,
                'has_price_history': self.has_price_history,
                'timestamp': datetime.utcnow().isoformat()
            },
            'user_data': {
                'has_bookmarked': self.user_has_bookmarked,
                'user_rating': self.user_rating
            }
        }