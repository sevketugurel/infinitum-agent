"""
Application layer - Contains use cases, commands, queries, and application services
"""

# Import main application services
from .services.product_search_service import ProductSearchService

# Import commands
from .commands.search_products_command import SearchProductsCommand, SearchProductsResult

# Import queries
from .queries.get_product_query import GetProductQuery, GetProductResult

# Import command handlers
from .commands.handlers.search_products_handler import SearchProductsHandler

# Import query handlers
from .queries.handlers.get_product_handler import (
    GetProductHandler, 
    GetProductListQuery, 
    GetProductListResult, 
    GetProductListHandler
)

__all__ = [
    # Services
    'ProductSearchService',
    
    # Commands
    'SearchProductsCommand', 'SearchProductsResult',
    
    # Queries
    'GetProductQuery', 'GetProductResult',
    'GetProductListQuery', 'GetProductListResult',
    
    # Handlers
    'SearchProductsHandler',
    'GetProductHandler', 'GetProductListHandler',
]