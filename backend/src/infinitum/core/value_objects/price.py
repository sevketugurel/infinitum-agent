"""
Price value object - Represents monetary values with currency
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any
import re
from decimal import Decimal, InvalidOperation


@dataclass(frozen=True)
class Price:
    """
    Price value object that encapsulates monetary values with currency.
    
    This is immutable (frozen=True) as value objects should be.
    """
    amount: Decimal
    currency: str = "USD"
    currency_symbol: str = "$"
    
    def __post_init__(self):
        """Validate price data after initialization"""
        if self.amount < 0:
            raise ValueError("Price amount cannot be negative")
        
        if not self.currency:
            raise ValueError("Currency cannot be empty")
        
        # Validate currency format (3-letter ISO code)
        if len(self.currency) != 3 or not self.currency.isalpha():
            raise ValueError("Currency must be a 3-letter ISO code (e.g., USD, EUR)")
    
    def is_valid(self) -> bool:
        """Check if price is valid (has positive amount)"""
        return self.amount > 0
    
    def is_free(self) -> bool:
        """Check if price is zero (free)"""
        return self.amount == 0
    
    def is_premium(self, threshold: Decimal = Decimal('100.00')) -> bool:
        """Check if price is considered premium (above threshold)"""
        return self.amount >= threshold
    
    def is_budget(self, threshold: Decimal = Decimal('50.00')) -> bool:
        """Check if price is considered budget-friendly (below threshold)"""
        return self.amount <= threshold
    
    def get_price_range(self) -> str:
        """Get price range category"""
        if self.is_free():
            return "free"
        elif self.is_budget():
            return "budget"
        elif self.is_premium():
            return "premium"
        else:
            return "mid-range"
    
    def format(self, include_currency: bool = True) -> str:
        """Format price as string"""
        if include_currency:
            return f"{self.currency_symbol}{self.amount:.2f}"
        else:
            return f"{self.amount:.2f}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            'amount': float(self.amount),
            'currency': self.currency,
            'currency_symbol': self.currency_symbol,
            'formatted': self.format(),
            'price_range': self.get_price_range()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Price':
        """Create Price from dictionary"""
        return cls(
            amount=Decimal(str(data['amount'])),
            currency=data.get('currency', 'USD'),
            currency_symbol=data.get('currency_symbol', '$')
        )
    
    @classmethod
    def from_string(cls, price_str: str) -> 'Price':
        """
        Create Price from string representation.
        
        Supports formats like:
        - "$99.99"
        - "€150.00"
        - "£75.50"
        - "¥1000"
        - "99.99 USD"
        - "150.00"
        """
        if not price_str or not isinstance(price_str, str):
            raise ValueError("Price string cannot be empty")
        
        price_str = price_str.strip()
        
        # Currency symbol mapping
        currency_map = {
            '$': ('USD', '$'),
            '€': ('EUR', '€'),
            '£': ('GBP', '£'),
            '¥': ('JPY', '¥'),
            '₹': ('INR', '₹'),
            '₽': ('RUB', '₽'),
            'C$': ('CAD', 'C$'),
            'A$': ('AUD', 'A$'),
        }
        
        # Try to extract currency symbol from beginning
        currency = "USD"
        currency_symbol = "$"
        amount_str = price_str
        
        for symbol, (curr, sym) in currency_map.items():
            if price_str.startswith(symbol):
                currency = curr
                currency_symbol = sym
                amount_str = price_str[len(symbol):].strip()
                break
        
        # Try to extract currency code from end (e.g., "99.99 USD")
        if currency == "USD":  # Only if we haven't found a symbol
            parts = price_str.split()
            if len(parts) == 2 and parts[1].upper() in [curr for curr, _ in currency_map.values()]:
                currency = parts[1].upper()
                currency_symbol = next(sym for curr, sym in currency_map.values() if curr == currency)
                amount_str = parts[0]
        
        # Extract numeric value using regex
        numeric_pattern = r'[\d,]+\.?\d*'
        match = re.search(numeric_pattern, amount_str)
        
        if not match:
            raise ValueError(f"Could not extract numeric value from price string: {price_str}")
        
        numeric_str = match.group().replace(',', '')
        
        try:
            amount = Decimal(numeric_str)
        except InvalidOperation:
            raise ValueError(f"Invalid numeric value in price string: {price_str}")
        
        return cls(amount=amount, currency=currency, currency_symbol=currency_symbol)
    
    @classmethod
    def zero(cls, currency: str = "USD", currency_symbol: str = "$") -> 'Price':
        """Create a zero price"""
        return cls(amount=Decimal('0.00'), currency=currency, currency_symbol=currency_symbol)
    
    def __str__(self) -> str:
        """String representation"""
        return self.format()
    
    def __lt__(self, other) -> bool:
        """Less than comparison (assumes same currency)"""
        if not isinstance(other, Price):
            return NotImplemented
        if self.currency != other.currency:
            raise ValueError("Cannot compare prices with different currencies")
        return self.amount < other.amount
    
    def __le__(self, other) -> bool:
        """Less than or equal comparison"""
        if not isinstance(other, Price):
            return NotImplemented
        if self.currency != other.currency:
            raise ValueError("Cannot compare prices with different currencies")
        return self.amount <= other.amount
    
    def __gt__(self, other) -> bool:
        """Greater than comparison"""
        if not isinstance(other, Price):
            return NotImplemented
        if self.currency != other.currency:
            raise ValueError("Cannot compare prices with different currencies")
        return self.amount > other.amount
    
    def __ge__(self, other) -> bool:
        """Greater than or equal comparison"""
        if not isinstance(other, Price):
            return NotImplemented
        if self.currency != other.currency:
            raise ValueError("Cannot compare prices with different currencies")
        return self.amount >= other.amount
    
    def __add__(self, other) -> 'Price':
        """Add two prices (must have same currency)"""
        if not isinstance(other, Price):
            return NotImplemented
        if self.currency != other.currency:
            raise ValueError("Cannot add prices with different currencies")
        return Price(
            amount=self.amount + other.amount,
            currency=self.currency,
            currency_symbol=self.currency_symbol
        )
    
    def __sub__(self, other) -> 'Price':
        """Subtract two prices (must have same currency)"""
        if not isinstance(other, Price):
            return NotImplemented
        if self.currency != other.currency:
            raise ValueError("Cannot subtract prices with different currencies")
        return Price(
            amount=self.amount - other.amount,
            currency=self.currency,
            currency_symbol=self.currency_symbol
        )
    
    def __mul__(self, factor: float) -> 'Price':
        """Multiply price by a factor"""
        if not isinstance(factor, (int, float, Decimal)):
            return NotImplemented
        return Price(
            amount=self.amount * Decimal(str(factor)),
            currency=self.currency,
            currency_symbol=self.currency_symbol
        )
    
    def __truediv__(self, divisor: float) -> 'Price':
        """Divide price by a divisor"""
        if not isinstance(divisor, (int, float, Decimal)):
            return NotImplemented
        if divisor == 0:
            raise ValueError("Cannot divide by zero")
        return Price(
            amount=self.amount / Decimal(str(divisor)),
            currency=self.currency,
            currency_symbol=self.currency_symbol
        )