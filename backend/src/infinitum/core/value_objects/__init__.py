"""
Value objects - Immutable objects that represent concepts
"""

from .price import Price
from .search_query import SearchQuery, SearchType, SearchIntent
from .user_preferences import UserPreferences, PriceRange, SortPreference, NotificationPreference

__all__ = [
    'Price',
    'SearchQuery', 'SearchType', 'SearchIntent',
    'UserPreferences', 'PriceRange', 'SortPreference', 'NotificationPreference',
]