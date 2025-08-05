"""
Dependency Injection Container - Wires together all application components
"""
from typing import Dict, Any, Optional

from ....shared.interfaces.repositories import (
    ProductRepository, UserRepository, SearchSessionRepository
)
from ....shared.interfaces.services import (
    SearchService, RecommendationService, AnalyticsService,
    NotificationService, ReviewService, UserService
)

from ....application.commands.handlers.search_products_handler import SearchProductsHandler
from ....application.queries.handlers.get_product_handler import GetProductHandler
from ....application.services.product_search_service import ProductSearchService

from ..persistence.repositories.product_repository import FirestoreProductRepository
from ..external.services.search_service_impl import SearchServiceImpl


class DIContainer:
    """
    Dependency Injection Container for managing application dependencies.
    
    This container follows the composition root pattern and provides
    a centralized place to configure all application dependencies.
    """
    
    def __init__(self):
        self._repositories: Dict[str, Any] = {}
        self._services: Dict[str, Any] = {}
        self._handlers: Dict[str, Any] = {}
        self._application_services: Dict[str, Any] = {}
        
        # Initialize all dependencies
        self._configure_repositories()
        self._configure_services()
        self._configure_handlers()
        self._configure_application_services()
    
    def _configure_repositories(self):
        """Configure repository implementations"""
        
        # Product Repository
        self._repositories['product_repository'] = FirestoreProductRepository()
        
        # TODO: Add other repository implementations
        # self._repositories['user_repository'] = FirestoreUserRepository()
        # self._repositories['search_session_repository'] = FirestoreSearchSessionRepository()
    
    def _configure_services(self):
        """Configure service implementations"""
        
        # Search Service
        self._services['search_service'] = SearchServiceImpl()
        
        # TODO: Add other service implementations
        # self._services['recommendation_service'] = RecommendationServiceImpl()
        # self._services['analytics_service'] = AnalyticsServiceImpl()
        # self._services['notification_service'] = NotificationServiceImpl()
    
    def _configure_handlers(self):
        """Configure command and query handlers"""
        
        # Command Handlers
        self._handlers['search_products_handler'] = SearchProductsHandler(
            product_repository=self.get_repository('product_repository'),
            search_service=self.get_service('search_service'),
            # search_session_repository=self.get_repository('search_session_repository'),
            # recommendation_service=self.get_service('recommendation_service')
        )
        
        # Query Handlers
        self._handlers['get_product_handler'] = GetProductHandler(
            product_repository=self.get_repository('product_repository'),
            # user_repository=self.get_repository('user_repository'),
            # recommendation_service=self.get_service('recommendation_service'),
            # review_service=self.get_service('review_service')
        )
    
    def _configure_application_services(self):
        """Configure application services"""
        
        # Product Search Service
        self._application_services['product_search_service'] = ProductSearchService(
            search_products_handler=self.get_handler('search_products_handler'),
            get_product_handler=self.get_handler('get_product_handler'),
            user_repository=None,  # TODO: Add when implemented
            search_session_repository=None,  # TODO: Add when implemented
            analytics_service=None,  # TODO: Add when implemented
            # recommendation_service=self.get_service('recommendation_service'),
            # notification_service=self.get_service('notification_service')
        )
    
    # Repository getters
    
    def get_repository(self, name: str) -> Any:
        """Get a repository by name"""
        if name not in self._repositories:
            raise ValueError(f"Repository '{name}' not found")
        return self._repositories[name]
    
    def get_product_repository(self) -> ProductRepository:
        """Get the product repository"""
        return self.get_repository('product_repository')
    
    def get_user_repository(self) -> Optional[UserRepository]:
        """Get the user repository"""
        return self._repositories.get('user_repository')
    
    def get_search_session_repository(self) -> Optional[SearchSessionRepository]:
        """Get the search session repository"""
        return self._repositories.get('search_session_repository')
    
    # Service getters
    
    def get_service(self, name: str) -> Any:
        """Get a service by name"""
        if name not in self._services:
            raise ValueError(f"Service '{name}' not found")
        return self._services[name]
    
    def get_search_service(self) -> SearchService:
        """Get the search service"""
        return self.get_service('search_service')
    
    def get_recommendation_service(self) -> Optional[RecommendationService]:
        """Get the recommendation service"""
        return self._services.get('recommendation_service')
    
    def get_analytics_service(self) -> Optional[AnalyticsService]:
        """Get the analytics service"""
        return self._services.get('analytics_service')
    
    def get_notification_service(self) -> Optional[NotificationService]:
        """Get the notification service"""
        return self._services.get('notification_service')
    
    def get_review_service(self) -> Optional[ReviewService]:
        """Get the review service"""
        return self._services.get('review_service')
    
    def get_user_service(self) -> Optional[UserService]:
        """Get the user service"""
        return self._services.get('user_service')
    
    # Handler getters
    
    def get_handler(self, name: str) -> Any:
        """Get a handler by name"""
        if name not in self._handlers:
            raise ValueError(f"Handler '{name}' not found")
        return self._handlers[name]
    
    def get_search_products_handler(self) -> SearchProductsHandler:
        """Get the search products command handler"""
        return self.get_handler('search_products_handler')
    
    def get_product_handler(self) -> GetProductHandler:
        """Get the get product query handler"""
        return self.get_handler('get_product_handler')
    
    # Application Service getters
    
    def get_application_service(self, name: str) -> Any:
        """Get an application service by name"""
        if name not in self._application_services:
            raise ValueError(f"Application service '{name}' not found")
        return self._application_services[name]
    
    def get_product_search_service(self) -> ProductSearchService:
        """Get the product search application service"""
        return self.get_application_service('product_search_service')
    
    # Utility methods
    
    def register_repository(self, name: str, repository: Any):
        """Register a custom repository"""
        self._repositories[name] = repository
        # Re-configure dependent components
        self._configure_handlers()
        self._configure_application_services()
    
    def register_service(self, name: str, service: Any):
        """Register a custom service"""
        self._services[name] = service
        # Re-configure dependent components
        self._configure_handlers()
        self._configure_application_services()
    
    def override_handler(self, name: str, handler: Any):
        """Override a handler with a custom implementation"""
        self._handlers[name] = handler
        # Re-configure dependent application services
        self._configure_application_services()
    
    def get_all_repositories(self) -> Dict[str, Any]:
        """Get all registered repositories"""
        return self._repositories.copy()
    
    def get_all_services(self) -> Dict[str, Any]:
        """Get all registered services"""
        return self._services.copy()
    
    def get_all_handlers(self) -> Dict[str, Any]:
        """Get all registered handlers"""
        return self._handlers.copy()
    
    def get_all_application_services(self) -> Dict[str, Any]:
        """Get all registered application services"""
        return self._application_services.copy()
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on all components"""
        health_status = {
            'status': 'healthy',
            'components': {},
            'timestamp': None
        }
        
        try:
            from datetime import datetime
            health_status['timestamp'] = datetime.utcnow().isoformat()
            
            # Check repositories
            health_status['components']['repositories'] = {
                'count': len(self._repositories),
                'registered': list(self._repositories.keys())
            }
            
            # Check services
            health_status['components']['services'] = {
                'count': len(self._services),
                'registered': list(self._services.keys())
            }
            
            # Check handlers
            health_status['components']['handlers'] = {
                'count': len(self._handlers),
                'registered': list(self._handlers.keys())
            }
            
            # Check application services
            health_status['components']['application_services'] = {
                'count': len(self._application_services),
                'registered': list(self._application_services.keys())
            }
            
            # Basic connectivity tests
            try:
                # Test product repository
                product_repo = self.get_product_repository()
                health_status['components']['product_repository'] = {
                    'status': 'healthy',
                    'type': type(product_repo).__name__
                }
            except Exception as e:
                health_status['components']['product_repository'] = {
                    'status': 'unhealthy',
                    'error': str(e)
                }
                health_status['status'] = 'degraded'
            
            try:
                # Test search service
                search_service = self.get_search_service()
                health_status['components']['search_service'] = {
                    'status': 'healthy',
                    'type': type(search_service).__name__
                }
            except Exception as e:
                health_status['components']['search_service'] = {
                    'status': 'unhealthy',
                    'error': str(e)
                }
                health_status['status'] = 'degraded'
            
        except Exception as e:
            health_status['status'] = 'unhealthy'
            health_status['error'] = str(e)
        
        return health_status


# Global container instance
container = DIContainer()


# Convenience functions for easy access
def get_product_repository() -> ProductRepository:
    """Get the product repository"""
    return container.get_product_repository()


def get_search_service() -> SearchService:
    """Get the search service"""
    return container.get_search_service()


def get_product_search_service() -> ProductSearchService:
    """Get the product search application service"""
    return container.get_product_search_service()


def get_search_products_handler() -> SearchProductsHandler:
    """Get the search products command handler"""
    return container.get_search_products_handler()


def get_product_handler() -> GetProductHandler:
    """Get the get product query handler"""
    return container.get_product_handler()


def get_container() -> DIContainer:
    """Get the global DI container"""
    return container


def configure_container_for_testing():
    """Configure container with test implementations"""
    # This would be used in tests to inject mock implementations
    pass


def reset_container():
    """Reset the container (useful for testing)"""
    global container
    container = DIContainer()