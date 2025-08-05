"""
Interfaces - Define contracts for repositories and services
"""

# Import repository interfaces
from .repositories import (
    Repository, ProductRepository, UserRepository, SearchSessionRepository,
    PackageRepository, ReviewRepository, AnalyticsRepository
)

# Import service interfaces
from .services import (
    SearchService, RecommendationService, ReviewService, UserService,
    NotificationService, AnalyticsService, CacheService, ExternalApiService,
    AIService, VectorSearchService
)

__all__ = [
    # Repository interfaces
    'Repository', 'ProductRepository', 'UserRepository', 'SearchSessionRepository',
    'PackageRepository', 'ReviewRepository', 'AnalyticsRepository',
    
    # Service interfaces
    'SearchService', 'RecommendationService', 'ReviewService', 'UserService',
    'NotificationService', 'AnalyticsService', 'CacheService', 'ExternalApiService',
    'AIService', 'VectorSearchService',
]