"""
Firestore-based Product Repository Implementation
"""
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
import uuid

from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from .....shared.interfaces.repositories import ProductRepository
from .....core.entities.product import Product
from .....shared.exceptions import NotFoundError, DatabaseError
from ..firestore_client import db


class FirestoreProductRepository(ProductRepository):
    """
    Firestore implementation of ProductRepository interface.
    
    This repository handles all product data persistence operations
    using Google Cloud Firestore as the backend.
    """
    
    def __init__(self):
        self.collection = db.collection('products')
        self.stats_collection = db.collection('product_stats')
    
    async def save(self, product: Product) -> None:
        """Save a product to Firestore"""
        try:
            product_data = product.to_dict()
            product_data['updated_at'] = datetime.utcnow().isoformat()
            
            # Use product_id as document ID
            doc_ref = self.collection.document(product.product_id)
            doc_ref.set(product_data, merge=True)
            
        except Exception as e:
            raise DatabaseError(f"Failed to save product {product.product_id}: {str(e)}")
    
    async def delete(self, product_id: str) -> bool:
        """Delete a product by ID"""
        try:
            doc_ref = self.collection.document(product_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                return False
            
            doc_ref.delete()
            
            # Also delete related stats
            stats_ref = self.stats_collection.document(product_id)
            if stats_ref.get().exists:
                stats_ref.delete()
            
            return True
            
        except Exception as e:
            raise DatabaseError(f"Failed to delete product {product_id}: {str(e)}")
    
    async def get_by_id(self, product_id: str) -> Optional[Product]:
        """Get a product by ID"""
        try:
            doc_ref = self.collection.document(product_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                return None
            
            product_data = doc.to_dict()
            product_data['product_id'] = product_id
            
            return Product.from_dict(product_data)
            
        except Exception as e:
            raise DatabaseError(f"Failed to get product {product_id}: {str(e)}")
    
    async def find_by_name(self, name: str) -> List[Product]:
        """Find products by name (case-insensitive partial match)"""
        try:
            # Firestore doesn't support case-insensitive queries directly
            # We'll do a range query and filter in memory
            name_lower = name.lower()
            
            # Query for products where name starts with the search term
            query = self.collection.where(
                filter=FieldFilter("name_lower", ">=", name_lower)
            ).where(
                filter=FieldFilter("name_lower", "<=", name_lower + "\uf8ff")
            ).limit(50)
            
            docs = query.stream()
            products = []
            
            for doc in docs:
                try:
                    product_data = doc.to_dict()
                    product_data['product_id'] = doc.id
                    
                    # Additional filtering for partial matches
                    if name_lower in product_data.get('name', '').lower():
                        product = Product.from_dict(product_data)
                        products.append(product)
                except Exception as parse_error:
                    print(f"Error parsing product {doc.id}: {parse_error}")
                    continue
            
            return products
            
        except Exception as e:
            raise DatabaseError(f"Failed to find products by name '{name}': {str(e)}")
    
    async def find_by_category(self, category: str, limit: int = 20, offset: int = 0) -> Tuple[List[Product], int]:
        """Find products by category with pagination"""
        try:
            # Get total count first
            count_query = self.collection.where(
                filter=FieldFilter("category", "==", category)
            )
            total_count = len(list(count_query.stream()))
            
            # Get paginated results
            query = self.collection.where(
                filter=FieldFilter("category", "==", category)
            ).order_by("updated_at", direction=firestore.Query.DESCENDING).limit(limit).offset(offset)
            
            docs = query.stream()
            products = []
            
            for doc in docs:
                try:
                    product_data = doc.to_dict()
                    product_data['product_id'] = doc.id
                    product = Product.from_dict(product_data)
                    products.append(product)
                except Exception as parse_error:
                    print(f"Error parsing product {doc.id}: {parse_error}")
                    continue
            
            return products, total_count
            
        except Exception as e:
            raise DatabaseError(f"Failed to find products by category '{category}': {str(e)}")
    
    async def find_by_brand(self, brand: str, limit: int = 20, offset: int = 0) -> Tuple[List[Product], int]:
        """Find products by brand with pagination"""
        try:
            # Get total count first
            count_query = self.collection.where(
                filter=FieldFilter("brand", "==", brand)
            )
            total_count = len(list(count_query.stream()))
            
            # Get paginated results
            query = self.collection.where(
                filter=FieldFilter("brand", "==", brand)
            ).order_by("updated_at", direction=firestore.Query.DESCENDING).limit(limit).offset(offset)
            
            docs = query.stream()
            products = []
            
            for doc in docs:
                try:
                    product_data = doc.to_dict()
                    product_data['product_id'] = doc.id
                    product = Product.from_dict(product_data)
                    products.append(product)
                except Exception as parse_error:
                    print(f"Error parsing product {doc.id}: {parse_error}")
                    continue
            
            return products, total_count
            
        except Exception as e:
            raise DatabaseError(f"Failed to find products by brand '{brand}': {str(e)}")
    
    async def find_with_filters(self, filters: Dict[str, Any], 
                               limit: int = 20, offset: int = 0, 
                               sort_by: str = "relevance") -> Tuple[List[Product], int]:
        """Find products with complex filters"""
        try:
            query = self.collection
            
            # Apply filters
            if 'category' in filters:
                query = query.where(filter=FieldFilter("category", "==", filters['category']))
            
            if 'brand' in filters:
                query = query.where(filter=FieldFilter("brand", "==", filters['brand']))
            
            if 'price_min' in filters:
                query = query.where(filter=FieldFilter("price.amount", ">=", filters['price_min']))
            
            if 'price_max' in filters:
                query = query.where(filter=FieldFilter("price.amount", "<=", filters['price_max']))
            
            if 'rating_min' in filters:
                query = query.where(filter=FieldFilter("rating", ">=", filters['rating_min']))
            
            if 'in_stock' in filters and filters['in_stock']:
                query = query.where(filter=FieldFilter("availability", "==", "in_stock"))
            
            # Apply sorting
            if sort_by == "price_asc":
                query = query.order_by("price.amount")
            elif sort_by == "price_desc":
                query = query.order_by("price.amount", direction=firestore.Query.DESCENDING)
            elif sort_by == "rating":
                query = query.order_by("rating", direction=firestore.Query.DESCENDING)
            elif sort_by == "newest":
                query = query.order_by("created_at", direction=firestore.Query.DESCENDING)
            else:  # relevance or default
                query = query.order_by("updated_at", direction=firestore.Query.DESCENDING)
            
            # Get total count (approximate - Firestore limitation)
            # For exact count, we'd need to run the query without limit/offset
            all_docs = list(query.stream())
            total_count = len(all_docs)
            
            # Apply pagination manually since we already have all docs
            paginated_docs = all_docs[offset:offset + limit]
            
            products = []
            for doc in paginated_docs:
                try:
                    product_data = doc.to_dict()
                    product_data['product_id'] = doc.id
                    product = Product.from_dict(product_data)
                    products.append(product)
                except Exception as parse_error:
                    print(f"Error parsing product {doc.id}: {parse_error}")
                    continue
            
            return products, total_count
            
        except Exception as e:
            raise DatabaseError(f"Failed to find products with filters: {str(e)}")
    
    async def search(self, query: str, filters: Optional[Dict[str, Any]] = None,
                    limit: int = 20, offset: int = 0) -> Tuple[List[Product], int]:
        """Search products by text query"""
        try:
            # Simple text search implementation
            # In production, you'd want to use a proper search service like Algolia or Elasticsearch
            
            query_lower = query.lower()
            all_products = []
            
            # Search in name, description, and brand
            # This is a simplified implementation - in production use proper full-text search
            docs = self.collection.limit(1000).stream()  # Limit to prevent memory issues
            
            for doc in docs:
                try:
                    product_data = doc.to_dict()
                    product_data['product_id'] = doc.id
                    
                    # Check if query matches name, description, or brand
                    name = product_data.get('name', '').lower()
                    description = product_data.get('description', '').lower()
                    brand = product_data.get('brand', '').lower()
                    
                    if (query_lower in name or 
                        query_lower in description or 
                        query_lower in brand):
                        
                        # Apply additional filters if provided
                        if filters:
                            if 'category' in filters and product_data.get('category') != filters['category']:
                                continue
                            if 'brand' in filters and product_data.get('brand') != filters['brand']:
                                continue
                            # Add more filter checks as needed
                        
                        product = Product.from_dict(product_data)
                        all_products.append(product)
                        
                except Exception as parse_error:
                    print(f"Error parsing product {doc.id}: {parse_error}")
                    continue
            
            # Sort by relevance (simple implementation)
            # Products with query in name get higher priority
            def relevance_score(product):
                score = 0
                if query_lower in product.name.lower():
                    score += 10
                if query_lower in product.brand.lower():
                    score += 5
                if query_lower in product.description.lower():
                    score += 1
                return score
            
            all_products.sort(key=relevance_score, reverse=True)
            
            # Apply pagination
            total_count = len(all_products)
            paginated_products = all_products[offset:offset + limit]
            
            return paginated_products, total_count
            
        except Exception as e:
            raise DatabaseError(f"Failed to search products with query '{query}': {str(e)}")
    
    async def get_popular_products(self, category: Optional[str] = None,
                                  limit: int = 20) -> List[Product]:
        """Get popular products"""
        try:
            query = self.collection
            
            if category:
                query = query.where(filter=FieldFilter("category", "==", category))
            
            # Order by popularity score or view count
            query = query.order_by("popularity_score", direction=firestore.Query.DESCENDING).limit(limit)
            
            docs = query.stream()
            products = []
            
            for doc in docs:
                try:
                    product_data = doc.to_dict()
                    product_data['product_id'] = doc.id
                    product = Product.from_dict(product_data)
                    products.append(product)
                except Exception as parse_error:
                    print(f"Error parsing product {doc.id}: {parse_error}")
                    continue
            
            return products
            
        except Exception as e:
            raise DatabaseError(f"Failed to get popular products: {str(e)}")
    
    async def get_featured_products(self, limit: int = 20) -> List[Product]:
        """Get featured products"""
        try:
            # Get products marked as featured or with high ratings
            query = self.collection.where(
                filter=FieldFilter("is_featured", "==", True)
            ).order_by("rating", direction=firestore.Query.DESCENDING).limit(limit)
            
            docs = query.stream()
            products = []
            
            for doc in docs:
                try:
                    product_data = doc.to_dict()
                    product_data['product_id'] = doc.id
                    product = Product.from_dict(product_data)
                    products.append(product)
                except Exception as parse_error:
                    print(f"Error parsing product {doc.id}: {parse_error}")
                    continue
            
            # If not enough featured products, fill with highly rated ones
            if len(products) < limit:
                remaining = limit - len(products)
                featured_ids = [p.product_id for p in products]
                
                additional_query = self.collection.where(
                    filter=FieldFilter("rating", ">=", 4.0)
                ).order_by("rating", direction=firestore.Query.DESCENDING).limit(remaining * 2)
                
                additional_docs = additional_query.stream()
                
                for doc in additional_docs:
                    if len(products) >= limit:
                        break
                    
                    if doc.id not in featured_ids:
                        try:
                            product_data = doc.to_dict()
                            product_data['product_id'] = doc.id
                            product = Product.from_dict(product_data)
                            products.append(product)
                        except Exception as parse_error:
                            print(f"Error parsing product {doc.id}: {parse_error}")
                            continue
            
            return products[:limit]
            
        except Exception as e:
            raise DatabaseError(f"Failed to get featured products: {str(e)}")
    
    async def update_stats(self, product_id: str, stats: Dict[str, Any]) -> None:
        """Update product statistics"""
        try:
            # Update stats in separate collection for better performance
            stats_ref = self.stats_collection.document(product_id)
            stats_data = {
                **stats,
                'updated_at': datetime.utcnow().isoformat(),
                'product_id': product_id
            }
            stats_ref.set(stats_data, merge=True)
            
            # Also update key stats in main product document
            product_ref = self.collection.document(product_id)
            update_data = {}
            
            if 'view_count' in stats:
                update_data['view_count'] = stats['view_count']
            if 'popularity_score' in stats:
                update_data['popularity_score'] = stats['popularity_score']
            if 'rating' in stats:
                update_data['rating'] = stats['rating']
            if 'review_count' in stats:
                update_data['review_count'] = stats['review_count']
            
            if update_data:
                update_data['updated_at'] = datetime.utcnow().isoformat()
                product_ref.update(update_data)
            
        except Exception as e:
            raise DatabaseError(f"Failed to update stats for product {product_id}: {str(e)}")
    
    async def batch_save(self, products: List[Product]) -> None:
        """Save multiple products in a batch operation"""
        try:
            batch = db.batch()
            
            for product in products:
                product_data = product.to_dict()
                product_data['updated_at'] = datetime.utcnow().isoformat()
                
                doc_ref = self.collection.document(product.product_id)
                batch.set(doc_ref, product_data, merge=True)
            
            batch.commit()
            
        except Exception as e:
            raise DatabaseError(f"Failed to batch save products: {str(e)}")
    
    async def get_products_by_ids(self, product_ids: List[str]) -> List[Product]:
        """Get multiple products by their IDs"""
        try:
            products = []
            
            # Firestore supports batch gets, but we'll use individual gets for simplicity
            for product_id in product_ids:
                try:
                    product = await self.get_by_id(product_id)
                    if product:
                        products.append(product)
                except Exception as e:
                    print(f"Error getting product {product_id}: {e}")
                    continue
            
            return products
            
        except Exception as e:
            raise DatabaseError(f"Failed to get products by IDs: {str(e)}")