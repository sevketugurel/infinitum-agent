"""
Product entity - Core domain model for products
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from datetime import datetime
from ..value_objects.price import Price


@dataclass
class Product:
    """
    Core Product entity representing a product in the system.
    
    This is the central domain entity that encapsulates all product-related
    business logic and rules.
    """
    id: str
    title: str
    brand: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    image_url: Optional[str] = None
    price: Optional[Price] = None
    rating: Optional[float] = None
    reviews_count: Optional[int] = None
    category: Optional[str] = None
    features: List[str] = None
    specifications: Dict[str, Any] = None
    availability: bool = True
    extraction_method: Optional[str] = None
    extracted_at: Optional[datetime] = None
    firestore_id: Optional[str] = None
    
    def __post_init__(self):
        """Post-initialization validation and setup"""
        if self.features is None:
            self.features = []
        if self.specifications is None:
            self.specifications = {}
        if self.extracted_at is None:
            self.extracted_at = datetime.now()
    
    def is_valid(self) -> bool:
        """
        Business rule: A product is valid if it has at least a title and ID
        """
        return bool(self.id and self.title and len(self.title.strip()) > 0)
    
    def has_price(self) -> bool:
        """Check if product has valid pricing information"""
        return self.price is not None and self.price.is_valid()
    
    def is_highly_rated(self, threshold: float = 4.0) -> bool:
        """Business rule: Product is highly rated if rating >= threshold"""
        return self.rating is not None and self.rating >= threshold
    
    def has_sufficient_reviews(self, min_reviews: int = 10) -> bool:
        """Business rule: Product has sufficient reviews for reliability"""
        return self.reviews_count is not None and self.reviews_count >= min_reviews
    
    def is_premium(self) -> bool:
        """Business rule: Determine if product is premium based on price"""
        if not self.has_price():
            return False
        return self.price.is_premium()
    
    def get_quality_score(self) -> float:
        """
        Calculate a quality score based on rating, reviews, and other factors
        Returns a score between 0.0 and 1.0
        """
        score = 0.0
        
        # Rating component (40% of score)
        if self.rating is not None:
            score += (self.rating / 5.0) * 0.4
        
        # Reviews count component (30% of score)
        if self.reviews_count is not None:
            # Normalize reviews count (100+ reviews = max score)
            normalized_reviews = min(self.reviews_count / 100.0, 1.0)
            score += normalized_reviews * 0.3
        
        # Availability component (20% of score)
        if self.availability:
            score += 0.2
        
        # Complete information component (10% of score)
        info_completeness = 0.0
        if self.description:
            info_completeness += 0.25
        if self.has_price():
            info_completeness += 0.25
        if self.image_url:
            info_completeness += 0.25
        if self.brand:
            info_completeness += 0.25
        
        score += info_completeness * 0.1
        
        return min(score, 1.0)
    
    def matches_category(self, category: str) -> bool:
        """Check if product matches a given category"""
        if not self.category:
            return False
        return category.lower() in self.category.lower()
    
    def has_feature(self, feature: str) -> bool:
        """Check if product has a specific feature"""
        feature_lower = feature.lower()
        
        # Check in features list
        if any(feature_lower in f.lower() for f in self.features):
            return True
        
        # Check in title
        if feature_lower in self.title.lower():
            return True
        
        # Check in description
        if self.description and feature_lower in self.description.lower():
            return True
        
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert product to dictionary representation"""
        return {
            'id': self.id,
            'title': self.title,
            'brand': self.brand,
            'description': self.description,
            'url': self.url,
            'image_url': self.image_url,
            'price': self.price.to_dict() if self.price else None,
            'rating': self.rating,
            'reviews_count': self.reviews_count,
            'category': self.category,
            'features': self.features,
            'specifications': self.specifications,
            'availability': self.availability,
            'extraction_method': self.extraction_method,
            'extracted_at': self.extracted_at.isoformat() if self.extracted_at else None,
            'firestore_id': self.firestore_id,
            'quality_score': self.get_quality_score()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Product':
        """Create Product instance from dictionary"""
        # Handle price conversion
        price = None
        if data.get('price'):
            if isinstance(data['price'], dict):
                price = Price.from_dict(data['price'])
            elif isinstance(data['price'], str):
                price = Price.from_string(data['price'])
        
        # Handle datetime conversion
        extracted_at = None
        if data.get('extracted_at'):
            if isinstance(data['extracted_at'], str):
                extracted_at = datetime.fromisoformat(data['extracted_at'])
            else:
                extracted_at = data['extracted_at']
        
        return cls(
            id=data['id'],
            title=data['title'],
            brand=data.get('brand'),
            description=data.get('description'),
            url=data.get('url'),
            image_url=data.get('image_url'),
            price=price,
            rating=data.get('rating'),
            reviews_count=data.get('reviews_count'),
            category=data.get('category'),
            features=data.get('features', []),
            specifications=data.get('specifications', {}),
            availability=data.get('availability', True),
            extraction_method=data.get('extraction_method'),
            extracted_at=extracted_at,
            firestore_id=data.get('firestore_id')
        )
    
    def __str__(self) -> str:
        """String representation of the product"""
        price_str = f" - {self.price}" if self.price else ""
        return f"{self.title} ({self.brand}){price_str}"
    
    def __eq__(self, other) -> bool:
        """Equality comparison based on ID"""
        if not isinstance(other, Product):
            return False
        return self.id == other.id
    
    def __hash__(self) -> int:
        """Hash based on ID for use in sets and dictionaries"""
        return hash(self.id)