"""
SearchSession entity - Represents a user's search session
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Set
from datetime import datetime, timedelta
from enum import Enum
import uuid

from ..value_objects.search_query import SearchQuery
from .product import Product


class SessionStatus(Enum):
    """Search session status"""
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    EXPIRED = "expired"


class SessionType(Enum):
    """Type of search session"""
    EXPLORATION = "exploration"  # Browsing/exploring
    RESEARCH = "research"  # Detailed research
    COMPARISON = "comparison"  # Comparing products
    PURCHASE_INTENT = "purchase_intent"  # Ready to buy
    SUPPORT = "support"  # Looking for help


@dataclass
class SearchResult:
    """Individual search result within a session"""
    query: SearchQuery
    products: List[Product]
    total_results: int
    search_time_ms: int
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def result_count(self) -> int:
        """Get number of products returned"""
        return len(self.products)
    
    @property
    def has_results(self) -> bool:
        """Check if search returned results"""
        return self.result_count > 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'query': self.query.to_dict(),
            'products': [p.to_dict() for p in self.products],
            'total_results': self.total_results,
            'result_count': self.result_count,
            'search_time_ms': self.search_time_ms,
            'timestamp': self.timestamp.isoformat(),
            'has_results': self.has_results
        }


@dataclass
class SearchSession:
    """
    SearchSession entity representing a user's search session.
    
    A session groups related searches and tracks user behavior.
    """
    # Identity
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    
    # Session metadata
    status: SessionStatus = SessionStatus.ACTIVE
    session_type: SessionType = SessionType.EXPLORATION
    
    # Timestamps
    started_at: datetime = field(default_factory=datetime.utcnow)
    last_activity_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    # Search data
    search_results: List[SearchResult] = field(default_factory=list)
    viewed_products: Set[str] = field(default_factory=set)  # Product IDs
    bookmarked_products: Set[str] = field(default_factory=set)  # Product IDs
    
    # Session context
    referrer: Optional[str] = None
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    
    # Analytics
    total_searches: int = 0
    total_results_viewed: int = 0
    session_duration_seconds: int = 0
    
    def __post_init__(self):
        """Initialize session data"""
        self.update_activity()
    
    @property
    def is_active(self) -> bool:
        """Check if session is active"""
        return self.status == SessionStatus.ACTIVE
    
    @property
    def is_expired(self) -> bool:
        """Check if session has expired (inactive for 30 minutes)"""
        if self.status != SessionStatus.ACTIVE:
            return False
        
        expiry_time = self.last_activity_at + timedelta(minutes=30)
        return datetime.utcnow() > expiry_time
    
    @property
    def duration(self) -> timedelta:
        """Get session duration"""
        end_time = self.completed_at or datetime.utcnow()
        return end_time - self.started_at
    
    @property
    def duration_minutes(self) -> float:
        """Get session duration in minutes"""
        return self.duration.total_seconds() / 60
    
    @property
    def has_searches(self) -> bool:
        """Check if session has any searches"""
        return len(self.search_results) > 0
    
    @property
    def has_results(self) -> bool:
        """Check if session has any search results"""
        return any(sr.has_results for sr in self.search_results)
    
    @property
    def unique_queries(self) -> List[str]:
        """Get unique search queries in this session"""
        queries = [sr.query.normalized_query for sr in self.search_results]
        return list(dict.fromkeys(queries))  # Preserve order, remove duplicates
    
    @property
    def most_recent_query(self) -> Optional[SearchQuery]:
        """Get the most recent search query"""
        if not self.search_results:
            return None
        return self.search_results[-1].query
    
    @property
    def total_products_found(self) -> int:
        """Get total number of products found across all searches"""
        return sum(sr.total_results for sr in self.search_results)
    
    @property
    def average_search_time(self) -> float:
        """Get average search time in milliseconds"""
        if not self.search_results:
            return 0.0
        
        total_time = sum(sr.search_time_ms for sr in self.search_results)
        return total_time / len(self.search_results)
    
    @property
    def engagement_score(self) -> float:
        """
        Calculate engagement score (0.0 to 1.0)
        Based on searches, views, bookmarks, and session duration
        """
        score = 0.0
        
        # Search activity (0.3 weight)
        if self.total_searches > 0:
            search_score = min(self.total_searches / 10, 1.0) * 0.3
            score += search_score
        
        # Product views (0.3 weight)
        if len(self.viewed_products) > 0:
            view_score = min(len(self.viewed_products) / 20, 1.0) * 0.3
            score += view_score
        
        # Bookmarks (0.2 weight)
        if len(self.bookmarked_products) > 0:
            bookmark_score = min(len(self.bookmarked_products) / 5, 1.0) * 0.2
            score += bookmark_score
        
        # Session duration (0.2 weight)
        duration_minutes = self.duration_minutes
        if duration_minutes > 0:
            # Optimal engagement around 5-15 minutes
            if duration_minutes <= 15:
                duration_score = (duration_minutes / 15) * 0.2
            else:
                # Diminishing returns after 15 minutes
                duration_score = max(0.2 - ((duration_minutes - 15) / 60), 0.05)
            score += duration_score
        
        return min(score, 1.0)
    
    def update_activity(self) -> None:
        """Update last activity timestamp"""
        self.last_activity_at = datetime.utcnow()
        
        # Check if session should be expired
        if self.is_expired and self.status == SessionStatus.ACTIVE:
            self.expire_session()
    
    def add_search_result(self, query: SearchQuery, products: List[Product], 
                         total_results: int, search_time_ms: int) -> None:
        """Add a search result to the session"""
        if not self.is_active:
            raise ValueError("Cannot add search results to inactive session")
        
        search_result = SearchResult(
            query=query,
            products=products,
            total_results=total_results,
            search_time_ms=search_time_ms
        )
        
        self.search_results.append(search_result)
        self.total_searches += 1
        self.total_results_viewed += len(products)
        
        # Update session type based on search patterns
        self._update_session_type(query)
        
        self.update_activity()
    
    def view_product(self, product_id: str) -> None:
        """Record that a product was viewed"""
        if not self.is_active:
            return
        
        self.viewed_products.add(product_id)
        self.update_activity()
    
    def bookmark_product(self, product_id: str) -> None:
        """Record that a product was bookmarked"""
        if not self.is_active:
            return
        
        self.bookmarked_products.add(product_id)
        self.update_activity()
    
    def remove_bookmark(self, product_id: str) -> None:
        """Remove a product bookmark"""
        self.bookmarked_products.discard(product_id)
        self.update_activity()
    
    def complete_session(self) -> None:
        """Mark session as completed"""
        if self.status == SessionStatus.ACTIVE:
            self.status = SessionStatus.COMPLETED
            self.completed_at = datetime.utcnow()
            self.session_duration_seconds = int(self.duration.total_seconds())
    
    def abandon_session(self) -> None:
        """Mark session as abandoned"""
        if self.status == SessionStatus.ACTIVE:
            self.status = SessionStatus.ABANDONED
            self.completed_at = datetime.utcnow()
            self.session_duration_seconds = int(self.duration.total_seconds())
    
    def expire_session(self) -> None:
        """Mark session as expired"""
        if self.status == SessionStatus.ACTIVE:
            self.status = SessionStatus.EXPIRED
            self.completed_at = datetime.utcnow()
            self.session_duration_seconds = int(self.duration.total_seconds())
    
    def _update_session_type(self, query: SearchQuery) -> None:
        """Update session type based on search patterns"""
        # Don't change if already determined to be purchase intent
        if self.session_type == SessionType.PURCHASE_INTENT:
            return
        
        # Check for purchase intent
        if query.search_intent.value == "buy":
            self.session_type = SessionType.PURCHASE_INTENT
            return
        
        # Check for comparison
        if query.contains_comparison or len(self.unique_queries) > 3:
            self.session_type = SessionType.COMPARISON
            return
        
        # Check for research
        if (query.search_intent.value == "research" or 
            query.get_complexity_score() > 0.7):
            self.session_type = SessionType.RESEARCH
            return
        
        # Check for support
        if query.search_intent.value == "support":
            self.session_type = SessionType.SUPPORT
            return
        
        # Default to exploration
        self.session_type = SessionType.EXPLORATION
    
    def get_search_patterns(self) -> Dict[str, Any]:
        """Analyze search patterns in this session"""
        if not self.search_results:
            return {
                'total_searches': 0,
                'unique_queries': 0,
                'query_refinements': 0,
                'common_search_types': [],
                'search_progression': []
            }
        
        from collections import Counter
        
        queries = [sr.query for sr in self.search_results]
        search_types = [q.search_type.value for q in queries]
        search_intents = [q.search_intent.value for q in queries]
        
        # Calculate query refinements (similar consecutive queries)
        refinements = 0
        for i in range(1, len(queries)):
            prev_keywords = set(queries[i-1].extract_keywords())
            curr_keywords = set(queries[i].extract_keywords())
            
            # If queries share keywords, it's likely a refinement
            if len(prev_keywords & curr_keywords) > 0:
                refinements += 1
        
        return {
            'total_searches': len(self.search_results),
            'unique_queries': len(self.unique_queries),
            'query_refinements': refinements,
            'common_search_types': Counter(search_types).most_common(3),
            'common_search_intents': Counter(search_intents).most_common(3),
            'search_progression': [
                {
                    'query': q.query,
                    'type': q.search_type.value,
                    'intent': q.search_intent.value,
                    'results': sr.result_count
                }
                for q, sr in zip(queries, self.search_results)
            ]
        }
    
    def get_product_interactions(self) -> Dict[str, Any]:
        """Get product interaction summary"""
        all_products = []
        for sr in self.search_results:
            all_products.extend(sr.products)
        
        return {
            'total_products_seen': len(all_products),
            'unique_products_seen': len(set(p.product_id for p in all_products)),
            'products_viewed': len(self.viewed_products),
            'products_bookmarked': len(self.bookmarked_products),
            'view_rate': len(self.viewed_products) / len(all_products) if all_products else 0,
            'bookmark_rate': len(self.bookmarked_products) / len(self.viewed_products) if self.viewed_products else 0
        }
    
    def to_dict(self, include_results: bool = True) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        data = {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'status': self.status.value,
            'session_type': self.session_type.value,
            'started_at': self.started_at.isoformat(),
            'last_activity_at': self.last_activity_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'duration_minutes': self.duration_minutes,
            'referrer': self.referrer,
            'user_agent': self.user_agent,
            'analytics': {
                'total_searches': self.total_searches,
                'total_results_viewed': self.total_results_viewed,
                'session_duration_seconds': self.session_duration_seconds,
                'engagement_score': self.engagement_score,
                'average_search_time_ms': self.average_search_time,
                'total_products_found': self.total_products_found
            },
            'interactions': self.get_product_interactions(),
            'search_patterns': self.get_search_patterns(),
            'metadata': {
                'is_active': self.is_active,
                'is_expired': self.is_expired,
                'has_searches': self.has_searches,
                'has_results': self.has_results,
                'unique_queries_count': len(self.unique_queries)
            }
        }
        
        if include_results:
            data['search_results'] = [sr.to_dict() for sr in self.search_results]
            data['viewed_products'] = list(self.viewed_products)
            data['bookmarked_products'] = list(self.bookmarked_products)
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SearchSession':
        """Create SearchSession from dictionary"""
        # Parse timestamps
        started_at = datetime.fromisoformat(data['started_at'].replace('Z', '+00:00'))
        last_activity_at = datetime.fromisoformat(data['last_activity_at'].replace('Z', '+00:00'))
        
        completed_at = None
        if data.get('completed_at'):
            completed_at = datetime.fromisoformat(data['completed_at'].replace('Z', '+00:00'))
        
        # Create session
        session = cls(
            session_id=data['session_id'],
            user_id=data.get('user_id'),
            status=SessionStatus(data.get('status', 'active')),
            session_type=SessionType(data.get('session_type', 'exploration')),
            started_at=started_at,
            last_activity_at=last_activity_at,
            completed_at=completed_at,
            referrer=data.get('referrer'),
            user_agent=data.get('user_agent'),
            ip_address=data.get('ip_address'),
            total_searches=data.get('analytics', {}).get('total_searches', 0),
            total_results_viewed=data.get('analytics', {}).get('total_results_viewed', 0),
            session_duration_seconds=data.get('analytics', {}).get('session_duration_seconds', 0)
        )
        
        # Add search results if present
        if data.get('search_results'):
            for sr_data in data['search_results']:
                query = SearchQuery.from_dict(sr_data['query'])
                products = [Product.from_dict(p) for p in sr_data['products']]
                
                search_result = SearchResult(
                    query=query,
                    products=products,
                    total_results=sr_data['total_results'],
                    search_time_ms=sr_data['search_time_ms'],
                    timestamp=datetime.fromisoformat(sr_data['timestamp'].replace('Z', '+00:00'))
                )
                session.search_results.append(search_result)
        
        # Add interactions
        if data.get('viewed_products'):
            session.viewed_products = set(data['viewed_products'])
        
        if data.get('bookmarked_products'):
            session.bookmarked_products = set(data['bookmarked_products'])
        
        return session
    
    @classmethod
    def create_for_user(cls, user_id: str, referrer: Optional[str] = None,
                       user_agent: Optional[str] = None) -> 'SearchSession':
        """Create a new search session for a user"""
        return cls(
            user_id=user_id,
            referrer=referrer,
            user_agent=user_agent
        )
    
    @classmethod
    def create_anonymous(cls, ip_address: Optional[str] = None) -> 'SearchSession':
        """Create a new anonymous search session"""
        return cls(ip_address=ip_address)
    
    def __str__(self) -> str:
        """String representation"""
        return f"SearchSession({self.session_id}, {self.status.value}, {self.total_searches} searches)"
    
    def __eq__(self, other) -> bool:
        """Equality comparison based on session_id"""
        if not isinstance(other, SearchSession):
            return False
        return self.session_id == other.session_id
    
    def __hash__(self) -> int:
        """Hash based on session_id"""
        return hash(self.session_id)