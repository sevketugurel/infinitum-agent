"""
User entity - Represents a user in the system
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
from enum import Enum

from ..value_objects.user_preferences import UserPreferences
from ..value_objects.search_query import SearchQuery


class UserRole(Enum):
    """User roles in the system"""
    GUEST = "guest"
    USER = "user"
    PREMIUM = "premium"
    ADMIN = "admin"


class UserStatus(Enum):
    """User account status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"


@dataclass
class User:
    """
    User entity representing a user in the system.
    
    This is a mutable entity (not frozen) as entities can change state.
    """
    # Identity
    user_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    email: Optional[str] = None
    username: Optional[str] = None
    
    # Profile
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    
    # System
    role: UserRole = UserRole.GUEST
    status: UserStatus = UserStatus.ACTIVE
    preferences: UserPreferences = field(default_factory=UserPreferences.default)
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_login_at: Optional[datetime] = None
    email_verified_at: Optional[datetime] = None
    
    # Usage tracking
    search_count: int = 0
    last_search_at: Optional[datetime] = None
    search_history: List[SearchQuery] = field(default_factory=list)
    
    # Subscription
    subscription_tier: str = "free"
    subscription_expires_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate user data after initialization"""
        if self.email and not self._is_valid_email(self.email):
            raise ValueError("Invalid email format")
        
        if self.username and not self._is_valid_username(self.username):
            raise ValueError("Invalid username format")
        
        if self.bio and len(self.bio) > 500:
            raise ValueError("Bio cannot exceed 500 characters")
    
    @staticmethod
    def _is_valid_email(email: str) -> bool:
        """Validate email format"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def _is_valid_username(username: str) -> bool:
        """Validate username format"""
        import re
        # Username: 3-30 chars, alphanumeric + underscore, no spaces
        pattern = r'^[a-zA-Z0-9_]{3,30}$'
        return re.match(pattern, username) is not None
    
    @property
    def full_name(self) -> str:
        """Get full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        else:
            return self.username or "Anonymous User"
    
    @property
    def display_name(self) -> str:
        """Get display name (username or full name)"""
        return self.username or self.full_name
    
    @property
    def is_guest(self) -> bool:
        """Check if user is a guest"""
        return self.role == UserRole.GUEST
    
    @property
    def is_registered(self) -> bool:
        """Check if user is registered (not guest)"""
        return self.role != UserRole.GUEST
    
    @property
    def is_premium(self) -> bool:
        """Check if user has premium access"""
        return self.role in [UserRole.PREMIUM, UserRole.ADMIN]
    
    @property
    def is_admin(self) -> bool:
        """Check if user is admin"""
        return self.role == UserRole.ADMIN
    
    @property
    def is_active(self) -> bool:
        """Check if user account is active"""
        return self.status == UserStatus.ACTIVE
    
    @property
    def is_email_verified(self) -> bool:
        """Check if email is verified"""
        return self.email_verified_at is not None
    
    @property
    def has_subscription(self) -> bool:
        """Check if user has active subscription"""
        if self.subscription_expires_at is None:
            return self.subscription_tier != "free"
        return datetime.utcnow() < self.subscription_expires_at
    
    @property
    def days_since_registration(self) -> int:
        """Get days since user registration"""
        return (datetime.utcnow() - self.created_at).days
    
    @property
    def days_since_last_login(self) -> Optional[int]:
        """Get days since last login"""
        if self.last_login_at is None:
            return None
        return (datetime.utcnow() - self.last_login_at).days
    
    @property
    def is_new_user(self) -> bool:
        """Check if user is new (registered within last 7 days)"""
        return self.days_since_registration <= 7
    
    @property
    def is_inactive_user(self) -> bool:
        """Check if user is inactive (no login in last 30 days)"""
        days_since_login = self.days_since_last_login
        return days_since_login is not None and days_since_login > 30
    
    @property
    def search_limit_reached(self) -> bool:
        """Check if user has reached search limit"""
        if self.is_premium:
            return False  # Premium users have unlimited searches
        
        # Free users: 100 searches per day
        if self.last_search_at is None:
            return False
        
        # Reset counter if last search was yesterday or earlier
        if (datetime.utcnow() - self.last_search_at).days >= 1:
            return False
        
        return self.search_count >= 100
    
    def update_profile(self, **kwargs) -> None:
        """Update user profile information"""
        allowed_fields = {
            'first_name', 'last_name', 'username', 'bio', 'avatar_url'
        }
        
        for field_name, value in kwargs.items():
            if field_name in allowed_fields:
                setattr(self, field_name, value)
        
        self.updated_at = datetime.utcnow()
    
    def update_preferences(self, preferences: UserPreferences) -> None:
        """Update user preferences"""
        self.preferences = preferences
        self.updated_at = datetime.utcnow()
    
    def record_login(self) -> None:
        """Record user login"""
        self.last_login_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def verify_email(self) -> None:
        """Mark email as verified"""
        self.email_verified_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        
        # Activate account if it was pending verification
        if self.status == UserStatus.PENDING_VERIFICATION:
            self.status = UserStatus.ACTIVE
    
    def suspend_account(self, reason: Optional[str] = None) -> None:
        """Suspend user account"""
        self.status = UserStatus.SUSPENDED
        self.updated_at = datetime.utcnow()
    
    def activate_account(self) -> None:
        """Activate user account"""
        self.status = UserStatus.ACTIVE
        self.updated_at = datetime.utcnow()
    
    def upgrade_to_premium(self, expires_at: Optional[datetime] = None) -> None:
        """Upgrade user to premium"""
        self.role = UserRole.PREMIUM
        self.subscription_tier = "premium"
        self.subscription_expires_at = expires_at
        self.updated_at = datetime.utcnow()
    
    def downgrade_to_free(self) -> None:
        """Downgrade user to free tier"""
        if self.role == UserRole.PREMIUM:
            self.role = UserRole.USER
        self.subscription_tier = "free"
        self.subscription_expires_at = None
        self.updated_at = datetime.utcnow()
    
    def record_search(self, search_query: SearchQuery) -> None:
        """Record a search query"""
        # Check if user can perform search
        if self.search_limit_reached:
            raise ValueError("Search limit reached for today")
        
        # Reset search count if it's a new day
        if (self.last_search_at is None or 
            (datetime.utcnow() - self.last_search_at).days >= 1):
            self.search_count = 0
        
        # Record the search
        self.search_count += 1
        self.last_search_at = datetime.utcnow()
        
        # Add to search history (keep only last 100 searches)
        if self.preferences.save_search_history:
            self.search_history.append(search_query)
            if len(self.search_history) > 100:
                self.search_history = self.search_history[-100:]
        
        self.updated_at = datetime.utcnow()
    
    def clear_search_history(self) -> None:
        """Clear user search history"""
        self.search_history = []
        self.updated_at = datetime.utcnow()
    
    def get_recent_searches(self, limit: int = 10) -> List[SearchQuery]:
        """Get recent search queries"""
        if not self.preferences.save_search_history:
            return []
        
        return self.search_history[-limit:] if self.search_history else []
    
    def get_search_patterns(self) -> Dict[str, Any]:
        """Analyze user search patterns"""
        if not self.search_history:
            return {
                'total_searches': 0,
                'unique_queries': 0,
                'avg_query_length': 0,
                'common_search_types': [],
                'common_intents': []
            }
        
        from collections import Counter
        
        queries = [sq.normalized_query for sq in self.search_history]
        search_types = [sq.search_type.value for sq in self.search_history]
        search_intents = [sq.search_intent.value for sq in self.search_history]
        
        return {
            'total_searches': len(self.search_history),
            'unique_queries': len(set(queries)),
            'avg_query_length': sum(len(q) for q in queries) / len(queries),
            'common_search_types': Counter(search_types).most_common(3),
            'common_intents': Counter(search_intents).most_common(3)
        }
    
    def can_perform_action(self, action: str) -> bool:
        """Check if user can perform a specific action"""
        if not self.is_active:
            return False
        
        action_permissions = {
            'search': True,  # All active users can search
            'save_preferences': self.is_registered,
            'view_history': self.is_registered,
            'unlimited_search': self.is_premium,
            'advanced_filters': self.is_premium,
            'export_data': self.is_premium,
            'admin_panel': self.is_admin,
        }
        
        return action_permissions.get(action, False)
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        data = {
            'user_id': self.user_id,
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.full_name,
            'display_name': self.display_name,
            'avatar_url': self.avatar_url,
            'bio': self.bio,
            'role': self.role.value,
            'status': self.status.value,
            'subscription_tier': self.subscription_tier,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'last_login_at': self.last_login_at.isoformat() if self.last_login_at else None,
            'metadata': {
                'is_guest': self.is_guest,
                'is_registered': self.is_registered,
                'is_premium': self.is_premium,
                'is_admin': self.is_admin,
                'is_active': self.is_active,
                'is_email_verified': self.is_email_verified,
                'has_subscription': self.has_subscription,
                'is_new_user': self.is_new_user,
                'days_since_registration': self.days_since_registration,
                'search_count': self.search_count,
                'search_patterns': self.get_search_patterns()
            }
        }
        
        if include_sensitive:
            data.update({
                'email': self.email,
                'email_verified_at': self.email_verified_at.isoformat() if self.email_verified_at else None,
                'subscription_expires_at': self.subscription_expires_at.isoformat() if self.subscription_expires_at else None,
                'preferences': self.preferences.to_dict(),
                'recent_searches': [sq.to_dict() for sq in self.get_recent_searches()]
            })
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """Create User from dictionary"""
        # Parse timestamps
        created_at = datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
        updated_at = datetime.fromisoformat(data['updated_at'].replace('Z', '+00:00'))
        
        last_login_at = None
        if data.get('last_login_at'):
            last_login_at = datetime.fromisoformat(data['last_login_at'].replace('Z', '+00:00'))
        
        email_verified_at = None
        if data.get('email_verified_at'):
            email_verified_at = datetime.fromisoformat(data['email_verified_at'].replace('Z', '+00:00'))
        
        subscription_expires_at = None
        if data.get('subscription_expires_at'):
            subscription_expires_at = datetime.fromisoformat(data['subscription_expires_at'].replace('Z', '+00:00'))
        
        # Parse preferences
        preferences = UserPreferences.default()
        if data.get('preferences'):
            preferences = UserPreferences.from_dict(data['preferences'])
        
        # Parse search history
        search_history = []
        if data.get('recent_searches'):
            search_history = [SearchQuery.from_dict(sq) for sq in data['recent_searches']]
        
        return cls(
            user_id=data['user_id'],
            email=data.get('email'),
            username=data.get('username'),
            first_name=data.get('first_name'),
            last_name=data.get('last_name'),
            avatar_url=data.get('avatar_url'),
            bio=data.get('bio'),
            role=UserRole(data.get('role', 'guest')),
            status=UserStatus(data.get('status', 'active')),
            preferences=preferences,
            created_at=created_at,
            updated_at=updated_at,
            last_login_at=last_login_at,
            email_verified_at=email_verified_at,
            search_count=data.get('search_count', 0),
            last_search_at=last_login_at,  # Approximation
            search_history=search_history,
            subscription_tier=data.get('subscription_tier', 'free'),
            subscription_expires_at=subscription_expires_at
        )
    
    @classmethod
    def create_guest(cls) -> 'User':
        """Create a guest user"""
        return cls(role=UserRole.GUEST)
    
    @classmethod
    def create_registered(cls, email: str, username: Optional[str] = None) -> 'User':
        """Create a registered user"""
        return cls(
            email=email,
            username=username,
            role=UserRole.USER,
            status=UserStatus.PENDING_VERIFICATION if email else UserStatus.ACTIVE
        )
    
    def __str__(self) -> str:
        """String representation"""
        return f"User({self.display_name}, {self.role.value})"
    
    def __eq__(self, other) -> bool:
        """Equality comparison based on user_id"""
        if not isinstance(other, User):
            return False
        return self.user_id == other.user_id
    
    def __hash__(self) -> int:
        """Hash based on user_id"""
        return hash(self.user_id)