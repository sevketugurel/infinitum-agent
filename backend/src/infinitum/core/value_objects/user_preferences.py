"""
UserPreferences value object - Represents user preferences and settings
"""
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Set
from enum import Enum
from decimal import Decimal


class PriceRange(Enum):
    """Price range preferences"""
    BUDGET = "budget"  # Under $50
    MID_RANGE = "mid_range"  # $50-$200
    PREMIUM = "premium"  # $200-$500
    LUXURY = "luxury"  # Over $500
    ANY = "any"


class SortPreference(Enum):
    """Sorting preferences"""
    RELEVANCE = "relevance"
    PRICE_LOW_TO_HIGH = "price_asc"
    PRICE_HIGH_TO_LOW = "price_desc"
    RATING = "rating"
    POPULARITY = "popularity"
    NEWEST = "newest"
    BRAND = "brand"


class NotificationPreference(Enum):
    """Notification preferences"""
    ALL = "all"
    IMPORTANT_ONLY = "important"
    NONE = "none"


@dataclass(frozen=True)
class UserPreferences:
    """
    UserPreferences value object that encapsulates user preferences and settings.
    
    This is immutable (frozen=True) as value objects should be.
    """
    # Search preferences
    preferred_categories: Optional[List[str]] = None
    excluded_categories: Optional[List[str]] = None
    preferred_brands: Optional[List[str]] = None
    excluded_brands: Optional[List[str]] = None
    
    # Price preferences
    price_range: PriceRange = PriceRange.ANY
    max_price: Optional[Decimal] = None
    min_price: Optional[Decimal] = None
    preferred_currency: str = "USD"
    
    # Display preferences
    sort_preference: SortPreference = SortPreference.RELEVANCE
    results_per_page: int = 20
    show_out_of_stock: bool = True
    show_price_history: bool = True
    
    # Quality preferences
    min_rating: Optional[float] = None
    require_reviews: bool = False
    min_review_count: Optional[int] = None
    
    # Feature preferences
    preferred_features: Optional[List[str]] = None
    required_features: Optional[List[str]] = None
    
    # Notification preferences
    notification_preference: NotificationPreference = NotificationPreference.IMPORTANT_ONLY
    email_notifications: bool = True
    push_notifications: bool = False
    
    # Privacy preferences
    save_search_history: bool = True
    personalized_recommendations: bool = True
    share_usage_data: bool = False
    
    def __post_init__(self):
        """Validate user preferences after initialization"""
        # Validate results per page
        if self.results_per_page < 1 or self.results_per_page > 100:
            raise ValueError("Results per page must be between 1 and 100")
        
        # Validate price range
        if self.min_price is not None and self.min_price < 0:
            raise ValueError("Minimum price cannot be negative")
        
        if self.max_price is not None and self.max_price < 0:
            raise ValueError("Maximum price cannot be negative")
        
        if (self.min_price is not None and self.max_price is not None 
            and self.min_price > self.max_price):
            raise ValueError("Minimum price cannot be greater than maximum price")
        
        # Validate rating
        if self.min_rating is not None and (self.min_rating < 0 or self.min_rating > 5):
            raise ValueError("Minimum rating must be between 0 and 5")
        
        # Validate review count
        if self.min_review_count is not None and self.min_review_count < 0:
            raise ValueError("Minimum review count cannot be negative")
        
        # Set default empty lists if None
        if self.preferred_categories is None:
            object.__setattr__(self, 'preferred_categories', [])
        if self.excluded_categories is None:
            object.__setattr__(self, 'excluded_categories', [])
        if self.preferred_brands is None:
            object.__setattr__(self, 'preferred_brands', [])
        if self.excluded_brands is None:
            object.__setattr__(self, 'excluded_brands', [])
        if self.preferred_features is None:
            object.__setattr__(self, 'preferred_features', [])
        if self.required_features is None:
            object.__setattr__(self, 'required_features', [])
    
    @property
    def has_price_constraints(self) -> bool:
        """Check if user has price constraints"""
        return (self.price_range != PriceRange.ANY or 
                self.min_price is not None or 
                self.max_price is not None)
    
    @property
    def has_quality_constraints(self) -> bool:
        """Check if user has quality constraints"""
        return (self.min_rating is not None or 
                self.require_reviews or 
                self.min_review_count is not None)
    
    @property
    def has_brand_preferences(self) -> bool:
        """Check if user has brand preferences"""
        return (len(self.preferred_brands) > 0 or 
                len(self.excluded_brands) > 0)
    
    @property
    def has_category_preferences(self) -> bool:
        """Check if user has category preferences"""
        return (len(self.preferred_categories) > 0 or 
                len(self.excluded_categories) > 0)
    
    @property
    def has_feature_preferences(self) -> bool:
        """Check if user has feature preferences"""
        return (len(self.preferred_features) > 0 or 
                len(self.required_features) > 0)
    
    @property
    def is_privacy_conscious(self) -> bool:
        """Check if user is privacy conscious"""
        return (not self.save_search_history or 
                not self.personalized_recommendations or 
                not self.share_usage_data)
    
    @property
    def wants_notifications(self) -> bool:
        """Check if user wants any notifications"""
        return (self.notification_preference != NotificationPreference.NONE and
                (self.email_notifications or self.push_notifications))
    
    def get_price_range_bounds(self) -> tuple[Optional[Decimal], Optional[Decimal]]:
        """Get actual price bounds based on price range preference"""
        if self.min_price is not None or self.max_price is not None:
            return (self.min_price, self.max_price)
        
        # Default ranges based on price range enum
        range_bounds = {
            PriceRange.BUDGET: (Decimal('0'), Decimal('50')),
            PriceRange.MID_RANGE: (Decimal('50'), Decimal('200')),
            PriceRange.PREMIUM: (Decimal('200'), Decimal('500')),
            PriceRange.LUXURY: (Decimal('500'), None),
            PriceRange.ANY: (None, None)
        }
        
        return range_bounds.get(self.price_range, (None, None))
    
    def matches_price(self, price: Decimal) -> bool:
        """Check if a price matches user preferences"""
        min_price, max_price = self.get_price_range_bounds()
        
        if min_price is not None and price < min_price:
            return False
        
        if max_price is not None and price > max_price:
            return False
        
        return True
    
    def matches_rating(self, rating: Optional[float]) -> bool:
        """Check if a rating matches user preferences"""
        if self.min_rating is None:
            return True
        
        if rating is None:
            return not self.require_reviews
        
        return rating >= self.min_rating
    
    def matches_review_count(self, review_count: Optional[int]) -> bool:
        """Check if review count matches user preferences"""
        if self.min_review_count is None:
            return True
        
        if review_count is None:
            return not self.require_reviews
        
        return review_count >= self.min_review_count
    
    def matches_brand(self, brand: str) -> bool:
        """Check if a brand matches user preferences"""
        brand_lower = brand.lower()
        
        # Check excluded brands first
        if any(excluded.lower() == brand_lower for excluded in self.excluded_brands):
            return False
        
        # If no preferred brands, accept any non-excluded brand
        if len(self.preferred_brands) == 0:
            return True
        
        # Check if brand is in preferred list
        return any(preferred.lower() == brand_lower for preferred in self.preferred_brands)
    
    def matches_category(self, category: str) -> bool:
        """Check if a category matches user preferences"""
        category_lower = category.lower()
        
        # Check excluded categories first
        if any(excluded.lower() == category_lower for excluded in self.excluded_categories):
            return False
        
        # If no preferred categories, accept any non-excluded category
        if len(self.preferred_categories) == 0:
            return True
        
        # Check if category is in preferred list
        return any(preferred.lower() == category_lower for preferred in self.preferred_categories)
    
    def matches_features(self, features: List[str]) -> bool:
        """Check if product features match user preferences"""
        features_lower = [f.lower() for f in features]
        
        # Check required features
        for required in self.required_features:
            if required.lower() not in features_lower:
                return False
        
        return True
    
    def get_preference_score(self, product_data: Dict[str, Any]) -> float:
        """
        Calculate preference score for a product (0.0 to 1.0)
        Higher score means better match to preferences
        """
        score = 0.0
        max_score = 0.0
        
        # Price preference (weight: 0.3)
        if 'price' in product_data:
            max_score += 0.3
            if self.matches_price(Decimal(str(product_data['price']))):
                score += 0.3
        
        # Rating preference (weight: 0.2)
        if 'rating' in product_data:
            max_score += 0.2
            if self.matches_rating(product_data['rating']):
                score += 0.2
        
        # Brand preference (weight: 0.2)
        if 'brand' in product_data:
            max_score += 0.2
            if self.matches_brand(product_data['brand']):
                score += 0.2
        
        # Category preference (weight: 0.15)
        if 'category' in product_data:
            max_score += 0.15
            if self.matches_category(product_data['category']):
                score += 0.15
        
        # Features preference (weight: 0.15)
        if 'features' in product_data:
            max_score += 0.15
            if self.matches_features(product_data['features']):
                score += 0.15
        
        return score / max_score if max_score > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            'search_preferences': {
                'preferred_categories': self.preferred_categories,
                'excluded_categories': self.excluded_categories,
                'preferred_brands': self.preferred_brands,
                'excluded_brands': self.excluded_brands,
            },
            'price_preferences': {
                'price_range': self.price_range.value,
                'max_price': float(self.max_price) if self.max_price else None,
                'min_price': float(self.min_price) if self.min_price else None,
                'preferred_currency': self.preferred_currency,
            },
            'display_preferences': {
                'sort_preference': self.sort_preference.value,
                'results_per_page': self.results_per_page,
                'show_out_of_stock': self.show_out_of_stock,
                'show_price_history': self.show_price_history,
            },
            'quality_preferences': {
                'min_rating': self.min_rating,
                'require_reviews': self.require_reviews,
                'min_review_count': self.min_review_count,
            },
            'feature_preferences': {
                'preferred_features': self.preferred_features,
                'required_features': self.required_features,
            },
            'notification_preferences': {
                'notification_preference': self.notification_preference.value,
                'email_notifications': self.email_notifications,
                'push_notifications': self.push_notifications,
            },
            'privacy_preferences': {
                'save_search_history': self.save_search_history,
                'personalized_recommendations': self.personalized_recommendations,
                'share_usage_data': self.share_usage_data,
            },
            'metadata': {
                'has_price_constraints': self.has_price_constraints,
                'has_quality_constraints': self.has_quality_constraints,
                'has_brand_preferences': self.has_brand_preferences,
                'has_category_preferences': self.has_category_preferences,
                'has_feature_preferences': self.has_feature_preferences,
                'is_privacy_conscious': self.is_privacy_conscious,
                'wants_notifications': self.wants_notifications,
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserPreferences':
        """Create UserPreferences from dictionary"""
        search_prefs = data.get('search_preferences', {})
        price_prefs = data.get('price_preferences', {})
        display_prefs = data.get('display_preferences', {})
        quality_prefs = data.get('quality_preferences', {})
        feature_prefs = data.get('feature_preferences', {})
        notification_prefs = data.get('notification_preferences', {})
        privacy_prefs = data.get('privacy_preferences', {})
        
        return cls(
            # Search preferences
            preferred_categories=search_prefs.get('preferred_categories'),
            excluded_categories=search_prefs.get('excluded_categories'),
            preferred_brands=search_prefs.get('preferred_brands'),
            excluded_brands=search_prefs.get('excluded_brands'),
            
            # Price preferences
            price_range=PriceRange(price_prefs.get('price_range', 'any')),
            max_price=Decimal(str(price_prefs['max_price'])) if price_prefs.get('max_price') else None,
            min_price=Decimal(str(price_prefs['min_price'])) if price_prefs.get('min_price') else None,
            preferred_currency=price_prefs.get('preferred_currency', 'USD'),
            
            # Display preferences
            sort_preference=SortPreference(display_prefs.get('sort_preference', 'relevance')),
            results_per_page=display_prefs.get('results_per_page', 20),
            show_out_of_stock=display_prefs.get('show_out_of_stock', True),
            show_price_history=display_prefs.get('show_price_history', True),
            
            # Quality preferences
            min_rating=quality_prefs.get('min_rating'),
            require_reviews=quality_prefs.get('require_reviews', False),
            min_review_count=quality_prefs.get('min_review_count'),
            
            # Feature preferences
            preferred_features=feature_prefs.get('preferred_features'),
            required_features=feature_prefs.get('required_features'),
            
            # Notification preferences
            notification_preference=NotificationPreference(notification_prefs.get('notification_preference', 'important')),
            email_notifications=notification_prefs.get('email_notifications', True),
            push_notifications=notification_prefs.get('push_notifications', False),
            
            # Privacy preferences
            save_search_history=privacy_prefs.get('save_search_history', True),
            personalized_recommendations=privacy_prefs.get('personalized_recommendations', True),
            share_usage_data=privacy_prefs.get('share_usage_data', False),
        )
    
    @classmethod
    def default(cls) -> 'UserPreferences':
        """Create default user preferences"""
        return cls()
    
    @classmethod
    def privacy_focused(cls) -> 'UserPreferences':
        """Create privacy-focused user preferences"""
        return cls(
            save_search_history=False,
            personalized_recommendations=False,
            share_usage_data=False,
            email_notifications=False,
            push_notifications=False,
            notification_preference=NotificationPreference.NONE
        )
    
    def __str__(self) -> str:
        """String representation"""
        constraints = []
        if self.has_price_constraints:
            constraints.append("price")
        if self.has_quality_constraints:
            constraints.append("quality")
        if self.has_brand_preferences:
            constraints.append("brand")
        if self.has_category_preferences:
            constraints.append("category")
        
        constraint_str = ", ".join(constraints) if constraints else "none"
        return f"UserPreferences(constraints: {constraint_str})"