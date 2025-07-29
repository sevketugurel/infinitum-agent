# File: app/crew/tools.py
from crewai.tools import BaseTool
import requests
from bs4 import BeautifulSoup
import os
import json

# You'll need a third-party service like SerpAPI for reliable Google Search
# Add its key to your .env file
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")

class SearchTool(BaseTool):
    name: str = "Google Search Tool"
    description: str = "A tool for performing Google searches to find relevant URLs and information."

    def _run(self, argument: str) -> str:
        """Searches Google using SerpAPI."""
        if not SERPAPI_API_KEY:
            return "Error: SERPAPI_API_KEY not configured"
        
        try:
            # Use the correct SerpAPI endpoint
            url = "https://serpapi.com/search"
            params = {
                "q": argument,
                "api_key": SERPAPI_API_KEY,
                "engine": "google",
                "num": 5  # Get top 5 results
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            # Parse the response to extract URLs
            data = response.json()
            if 'organic_results' in data and data['organic_results']:
                results = []
                for result in data['organic_results'][:5]:  # Get top 5 results
                    results.append(f"Title: {result.get('title', 'N/A')}\nURL: {result.get('link', 'N/A')}\nSnippet: {result.get('snippet', 'N/A')}\n")
                return "\n".join(results)
            else:
                return "No search results found"
                
        except Exception as e:
            return f"Search error: {str(e)}"

class ScrapeWebsiteTool(BaseTool):
    name: str = "Website Scraping Tool"
    description: str = "Scrapes a given URL to extract product information in a structured format."

    def _run(self, argument: str) -> str:
        """Scrapes a URL and returns structured product information."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
            }
            response = requests.get(argument, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract title
            title = self._extract_title(soup)
            
            # Extract price
            price = self._extract_price(soup)
            
            # Extract brand
            brand = self._extract_brand(soup)
            
            # Extract image
            image_url = self._extract_image(soup)
            
            # Extract description
            description = self._extract_description(soup)
            
            # Return structured information
            result = f"""
PRODUCT INFORMATION EXTRACTED:

Title: {title}
Price: {price}
Brand: {brand}
Image URL: {image_url}
Description: {description}

URL: {argument}
"""
            return result.strip()
            
        except Exception as e:
            return f"Scraping error: {str(e)}"
    
    def _extract_title(self, soup):
        """Extract product title from various possible selectors."""
        selectors = [
            '#productTitle',
            'h1[data-automation-id="product-title"]',
            'h1.it-ttl',
            '.pdp-product-name',
            'h1.product-title',
            'h1',
            'title'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text().strip()
                if text and len(text) > 10:  # Ensure it's a meaningful title
                    return text
        
        return "Product title not found"
    
    def _extract_price(self, soup):
        """Extract price from various possible selectors."""
        selectors = [
            '.a-price-whole',
            '.a-price .a-offscreen',
            '.notranslate',
            '[data-automation-id="product-price"]',
            '.price',
            '.current-price',
            '.sale-price'
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text().strip()
                # Look for price patterns like $299.99, £199, €150, etc.
                if any(char in text for char in ['$', '£', '€', '¥']) and any(char.isdigit() for char in text):
                    # Clean up the price text
                    price = text.replace('\n', '').replace('  ', ' ').strip()
                    if len(price) < 20:  # Ensure it's not too long
                        return price
        
        return "Price not found"
    
    def _extract_brand(self, soup):
        """Extract brand from various possible selectors."""
        selectors = [
            '[data-automation-id="product-brand"]',
            '.brand',
            '.manufacturer',
            '#brand',
            '.product-brand'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text().strip()
                if text and len(text) < 50:  # Ensure it's a reasonable brand name
                    return text
        
        # Try to extract from title
        title_element = soup.select_one('#productTitle, h1')
        if title_element:
            title = title_element.get_text().strip()
            # Common brand patterns
            brands = ['Sony', 'Apple', 'Samsung', 'Amazon', 'Nike', 'Adidas', 'Microsoft', 'Google', 'Bose']
            for brand in brands:
                if brand.lower() in title.lower():
                    return brand
        
        return "Brand not found"
    
    def _extract_image(self, soup):
        """Extract main product image URL."""
        selectors = [
            '#landingImage',
            '.product-image img',
            '.main-image img',
            '.primary-image img',
            'img[data-automation-id="product-image"]'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                # Try different image URL attributes
                for attr in ['src', 'data-src', 'data-lazy-src']:
                    img_url = element.get(attr)
                    if img_url and ('http' in img_url or img_url.startswith('//')):
                        return img_url if img_url.startswith('http') else f"https:{img_url}"
        
        return "Image not found"
    
    def _extract_description(self, soup):
        """Extract product description."""
        selectors = [
            '#feature-bullets ul',
            '.product-description',
            '.product-details',
            '[data-automation-id="product-description"]',
            '#productDescription'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text().strip()
                # Clean up and limit description
                if text and len(text) > 20:
                    description = ' '.join(text.split()[:50])  # Limit to 50 words
                    return description
        
        return "Description not found"