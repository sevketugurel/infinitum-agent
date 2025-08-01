# File: src/infinitum/services/crawl4ai_service.py
import asyncio
from typing import Dict, Optional, Any
import json
from crawl4ai import AsyncWebCrawler
from crawl4ai.extraction_strategy import LLMExtractionStrategy, LLMConfig
from infinitum.infrastructure.external_services.vertex_ai import ask_gemini
import traceback

async def get_structured_data(url: str) -> Dict[str, Any]:
    """
    Extract structured product data from a URL using Crawl4AI.
    
    Args:
        url (str): The product page URL to scrape
        
    Returns:
        Dict[str, Any]: Structured product data with keys:
            - title: Product title
            - price: Product price with currency
            - brand: Product brand
            - image: Main product image URL
            - description: Product description
            - url: Source URL
            - extraction_method: Method used for extraction
    """
    
    # Define the extraction schema
    schema = {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "The main product title or name"
            },
            "price": {
                "type": "string", 
                "description": "The product price with currency symbol (e.g., '$299.99')"
            },
            "brand": {
                "type": "string",
                "description": "The product brand or manufacturer"
            },
            "image": {
                "type": "string",
                "description": "URL of the main product image"
            },
            "description": {
                "type": "string",
                "description": "Product description or key features (keep under 200 characters)"
            }
        },
        "required": ["title"]
    }
    
    async with AsyncWebCrawler(verbose=False) as crawler:
        try:
            # Skip LLM extraction strategy for now - use basic crawling then Gemini fallback
            extraction_strategy = None
            
            # Crawl the page with better anti-bot protection
            result = await crawler.arun(
                url=url,
                bypass_cache=True,
                js_code=[
                    "window.scrollTo(0, document.body.scrollHeight/3);",  # Scroll gradually
                    "await new Promise(resolve => setTimeout(resolve, 1000));",  # Wait 1 second
                    "window.scrollTo(0, document.body.scrollHeight);"
                ],
                wait_for="css:body",
                timeout=40,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1'
                }
            )
            
            if result.success and result.cleaned_html:
                # Use Gemini to extract from the crawled HTML
                return await _fallback_extraction(url, result.cleaned_html)
            else:
                print(f"Crawl4AI failed: {result.error_message if hasattr(result, 'error_message') else 'Unknown error'}")
                # Fallback to basic extraction
                return await _fallback_extraction(url)
                
        except Exception as e:
            print(f"Crawl4AI error: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            # Fallback to basic extraction
            return await _fallback_extraction(url)

async def _fallback_extraction(url: str, html_content: Optional[str] = None) -> Dict[str, Any]:
    """
    Fallback extraction using Gemini directly on HTML content.
    """
    try:
        if not html_content:
            # If no HTML provided, do a basic crawl to get content
            async with AsyncWebCrawler(verbose=False) as crawler:
                result = await crawler.arun(url=url, timeout=20)
                if result.success:
                    html_content = result.cleaned_html[:15000]  # Increased to 15k chars for better price detection
                else:
                    raise Exception(f"Failed to crawl URL: {url}")
        
        # Use Gemini to extract product data from HTML
        prompt = f"""
        Extract product information from this HTML content and return ONLY a valid JSON object.
        
        IMPORTANT: Look carefully for price information in these common formats:
        - $99.99, $199, €150, £120
        - "price": "$99.99", "cost": "$199"
        - class="price", class="cost", class="amount"
        - data-price, data-cost attributes
        - Text near words like "Price:", "Cost:", "$", "USD", "EUR"
        
        HTML Content:
        {html_content[:12000]}  
        
        Return JSON with this structure:
        {{
            "title": "product title",
            "price": "price with currency symbol (e.g. $99.99)",
            "brand": "brand name", 
            "image": "full image URL",
            "description": "brief description under 200 chars"
        }}
        
        CRITICAL: If you find ANY price information, include it. Look for:
        - Sale prices, regular prices, discounted prices
        - Text like "Now $99", "Was $199 Now $149", "Starting at $99"
        - Price ranges like "$99-$199"
        
        Use null for missing information. Return ONLY the JSON, no other text.
        """
        
        gemini_response = ask_gemini(prompt)
        
        # Try to parse the JSON from Gemini's response
        try:
            # Extract JSON from response (Gemini might add extra text)
            json_start = gemini_response.find('{')
            json_end = gemini_response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = gemini_response[json_start:json_end]
                product_data = json.loads(json_str)
            else:
                raise ValueError("No JSON found in Gemini response")
                
            # Add metadata
            product_data["url"] = url
            product_data["extraction_method"] = "gemini_fallback"
            
            return _clean_product_data(product_data)
            
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Failed to parse Gemini JSON response: {e}")
            print(f"Gemini response: {gemini_response}")
            
            # Try regex-based price extraction as fallback
            import re
            fallback_price = None
            price_patterns = [
                r'\$([0-9,]+\.?[0-9]*)',  # $99.99, $1,299
                r'([0-9,]+\.?[0-9]*)\s*USD',  # 99.99 USD
                r'Price:\s*\$([0-9,]+\.?[0-9]*)',  # Price: $99.99
                r'€([0-9,]+\.?[0-9]*)',  # €99.99
                r'£([0-9,]+\.?[0-9]*)',  # £99.99
            ]
            
            for pattern in price_patterns:
                match = re.search(pattern, html_content)
                if match:
                    fallback_price = f"${match.group(1)}"
                    break
            
            # Final fallback - return basic structure with any found price
            return {
                "title": "Product title not found",
                "price": fallback_price,
                "brand": None, 
                "image": None,
                "description": None,
                "url": url,
                "extraction_method": "regex_fallback" if fallback_price else "fallback_failed",
                "error": f"Extraction failed: {str(e)}"
            }
            
    except Exception as e:
        print(f"Fallback extraction failed: {str(e)}")
        return {
            "title": "Extraction failed",
            "price": None,
            "brand": None,
            "image": None, 
            "description": None,
            "url": url,
            "extraction_method": "fallback_failed",
            "error": str(e)
        }

def _clean_product_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Clean and validate product data."""
    cleaned = {}
    
    # Clean title
    title = data.get("title")
    if title and isinstance(title, str):
        title = title.strip()
        cleaned["title"] = title if title and title.lower() != "null" else "Product title not found"
    else:
        cleaned["title"] = "Product title not found"
    
    # Clean price
    price = data.get("price")
    if price and isinstance(price, str):
        price = price.strip()
        if price and price.lower() not in ["null", "none", ""]:
            cleaned["price"] = price
        else:
            cleaned["price"] = None
    else:
        cleaned["price"] = None
    
    # Clean brand  
    brand = data.get("brand")
    if brand and isinstance(brand, str):
        brand = brand.strip()
        if brand and brand.lower() not in ["null", "none", ""]:
            cleaned["brand"] = brand
        else:
            cleaned["brand"] = None
    else:
        cleaned["brand"] = None
    
    # Clean image URL
    image = data.get("image")
    if image and isinstance(image, str):
        image = image.strip()
        if image and image.lower() not in ["null", "none", ""] and "http" in image:
            cleaned["image"] = image
        else:
            cleaned["image"] = None
    else:
        cleaned["image"] = None
    
    # Clean description
    description = data.get("description")
    if description and isinstance(description, str):
        description = description.strip()
        if description and description.lower() not in ["null", "none", ""]:
            # Limit description length
            cleaned["description"] = description[:200] + "..." if len(description) > 200 else description
        else:
            cleaned["description"] = None
    else:
        cleaned["description"] = None
    
    # Copy metadata
    cleaned["url"] = data.get("url")
    cleaned["extraction_method"] = data.get("extraction_method", "unknown")
    
    if "error" in data:
        cleaned["error"] = data["error"]
    
    return cleaned

# Synchronous wrapper for the async function
def get_structured_data_sync(url: str) -> Dict[str, Any]:
    """
    Synchronous wrapper for get_structured_data.
    
    Args:
        url (str): The product page URL to scrape
        
    Returns:
        Dict[str, Any]: Structured product data
    """
    import asyncio
    import nest_asyncio
    
    try:
        # Allow nested event loops (needed when FastAPI is already running)
        nest_asyncio.apply()
        
        # Try to get existing loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, use nest_asyncio to handle nested execution
                return asyncio.create_task(get_structured_data(url)).result()
        except RuntimeError:
            pass
        
        # Create new loop if needed
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(get_structured_data(url))
        
    except Exception as e:
        # Fallback: run in thread pool to avoid event loop conflicts
        import concurrent.futures
        import threading
        
        def run_in_thread():
            # Create new event loop in thread
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                return new_loop.run_until_complete(get_structured_data(url))
            finally:
                new_loop.close()
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_in_thread)
            return future.result(timeout=60)  # 60 second timeout 