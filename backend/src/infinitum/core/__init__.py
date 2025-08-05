"""
Core domain layer - Contains business entities and value objects
"""

# Import entities
from .entities.product import Product
from .entities.user import User, UserRole, UserStatus
from .entities.search_session import SearchSession, SearchResult, SessionStatus, SessionType
from .entities.package import Package, PackageType, PackageStatus, LicenseType, PackageVersion, PackageDependency

# Import value objects
from .value_objects.price import Price
from .value_objects.search_query import SearchQuery, SearchType, SearchIntent
from .value_objects.user_preferences import (
    UserPreferences, 
    PriceRange, 
    SortPreference, 
    NotificationPreference
)

__all__ = [
    # Entities
    'Product',
    'User', 'UserRole', 'UserStatus',
    'SearchSession', 'SearchResult', 'SessionStatus', 'SessionType',
    'Package', 'PackageType', 'PackageStatus', 'LicenseType', 'PackageVersion', 'PackageDependency',
    
    # Value Objects
    'Price',
    'SearchQuery', 'SearchType', 'SearchIntent',
    'UserPreferences', 'PriceRange', 'SortPreference', 'NotificationPreference',
]