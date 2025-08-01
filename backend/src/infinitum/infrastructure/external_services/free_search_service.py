# File: src/infinitum/services/free_search_service.py
"""
Free search service using DuckDuckGo and other free alternatives to replace SerpAPI
"""

import os
import requests
import json
import logging
import time
import random
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
from infinitum.settings import settings

logger = logging.getLogger(__name__)

# Circuit breaker state
_circuit_breaker = {
    "failures": 0,
    "last_failure_time": 0,
    "circuit_open": False,
    "failure_threshold": 5,
    "recovery_timeout": 300  # 5 minutes
}

# Cache for recent searches
_search_cache = {}
_cache_ttl = 300  # 5 minutes cache

def _check_circuit_breaker() -> bool:
    """Check if circuit breaker should allow requests"""
    current_time = time.time()
    
    if _circuit_breaker["circuit_open"]:
        if current_time - _circuit_breaker["last_failure_time"] > _circuit_breaker["recovery_timeout"]:
            _circuit_breaker["circuit_open"] = False
            _circuit_breaker["failures"] = 0
            logger.info("Circuit breaker reset - attempting search again")
            return True
        else:
            logger.warning("Circuit breaker open - using fallback immediately")
            return False
    
    return True

def _record_failure():
    """Record a failure and potentially open circuit breaker"""
    _circuit_breaker["failures"] += 1
    _circuit_breaker["last_failure_time"] = time.time()
    
    if _circuit_breaker["failures"] >= _circuit_breaker["failure_threshold"]:
        _circuit_breaker["circuit_open"] = True
        logger.warning(f"Circuit breaker opened after {_circuit_breaker['failures']} failures")

def _record_success():
    """Record a successful request"""
    _circuit_breaker["failures"] = 0

def add_rate_limit_delay():
    """Add minimal delay between requests to respect rate limits"""
    if _circuit_breaker["circuit_open"]:
        logger.debug("Circuit breaker open - skipping rate limit delay")
        return
        
    delay = random.uniform(0.1, 0.3)  # 0.1-0.3 seconds
    logger.debug(f"Adding minimal rate limit delay of {delay:.1f}s")
    time.sleep(delay)

def search_duckduckgo(query: str, num_results: int = 10) -> List[Dict[str, Any]]:
    """
    Search using DuckDuckGo Instant Answer API (free, no API key required)
    
    Args:
        query (str): Search query string
        num_results (int): Number of results to return
        
    Returns:
        List[Dict[str, Any]]: List of search results
    """
    
    # Check cache first
    cache_key = f"ddg_{query}_{num_results}"
    if cache_key in _search_cache:
        cache_time, cached_results = _search_cache[cache_key]
        if time.time() - cache_time < _cache_ttl:
            logger.info(f"⚡ Returning cached DuckDuckGo results for: '{query}'")
            return cached_results
        else:
            del _search_cache[cache_key]
    
    if not _check_circuit_breaker():
        raise RuntimeError("Circuit breaker open - API temporarily disabled")
    
    try:
        logger.info(f"🔍 DuckDuckGo search for: '{query}' (limit: {num_results})")
        
        add_rate_limit_delay()
        
        # DuckDuckGo Instant Answer API
        url = "https://api.duckduckgo.com/"
        params = {
            "q": query,
            "format": "json",
            "no_html": "1",
            "skip_disambig": "1"
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Extract results from DuckDuckGo response
        results = []
        
        # Add instant answer if available
        if data.get("Answer"):
            results.append({
                "title": "Instant Answer",
                "link": data.get("AnswerURL", ""),
                "snippet": data.get("Answer", ""),
                "position": 1,
                "displayed_link": "duckduckgo.com",
                "source": "duckduckgo"
            })
        
        # Add abstract if available
        if data.get("Abstract"):
            results.append({
                "title": data.get("Heading", "Abstract"),
                "link": data.get("AbstractURL", ""),
                "snippet": data.get("Abstract", ""),
                "position": len(results) + 1,
                "displayed_link": "duckduckgo.com",
                "source": "duckduckgo"
            })
        
        # Add related topics
        for topic in data.get("RelatedTopics", [])[:num_results - len(results)]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append({
                    "title": topic.get("FirstURL", "").split("/")[-1].replace("_", " ").title(),
                    "link": topic.get("FirstURL", ""),
                    "snippet": topic.get("Text", ""),
                    "position": len(results) + 1,
                    "displayed_link": "duckduckgo.com",
                    "source": "duckduckgo"
                })
        
        # If we don't have enough results, try web scraping fallback
        if len(results) < num_results:
            logger.info(f"DuckDuckGo returned {len(results)} results, trying web scraping fallback")
            web_results = search_duckduckgo_web(query, num_results - len(results))
            for result in web_results:
                result["position"] = len(results) + 1
                results.append(result)
        
        # Cache results
        _search_cache[cache_key] = (time.time(), results)
        _record_success()
        
        logger.info(f"Found {len(results)} DuckDuckGo results for: '{query}'")
        return results[:num_results]
        
    except Exception as e:
        _record_failure()
        logger.error(f"DuckDuckGo search failed: {str(e)}")
        raise

def search_duckduckgo_web(query: str, num_results: int = 10) -> List[Dict[str, Any]]:
    """
    Web scraping fallback for DuckDuckGo search results
    """
    try:
        logger.info(f"🌐 DuckDuckGo web scraping for: '{query}'")
        
        # Use DuckDuckGo web search
        search_url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        response = requests.get(search_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        results = []
        
        # Find search result links
        for result in soup.find_all('a', class_='result__a')[:num_results]:
            title = result.get_text(strip=True)
            link = result.get('href', '')
            
            # Find snippet (next sibling with class result__snippet)
            snippet_elem = result.find_next_sibling(class_='result__snippet')
            snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
            
            if title and link:
                results.append({
                    "title": title,
                    "link": link,
                    "snippet": snippet,
                    "position": len(results) + 1,
                    "displayed_link": "duckduckgo.com",
                    "source": "duckduckgo_web"
                })
        
        return results
        
    except Exception as e:
        logger.error(f"DuckDuckGo web scraping failed: {str(e)}")
        return []

def search_bing_web(query: str, num_results: int = 10) -> List[Dict[str, Any]]:
    """
    Search using Bing Web Search API (requires Azure API key)
    Free tier: 1,000 searches/month
    """
    
    bing_api_key = settings.BING_API_KEY
    if not bing_api_key:
        logger.warning("Bing API key not configured")
        return []
    
    try:
        logger.info(f"🔍 Bing search for: '{query}' (limit: {num_results})")
        
        add_rate_limit_delay()
        
        url = "https://api.bing.microsoft.com/v7.0/search"
        headers = {
            "Ocp-Apim-Subscription-Key": bing_api_key
        }
        params = {
            "q": query,
            "count": min(num_results, 50),
            "mkt": "en-US",
            "safesearch": "moderate"
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        web_pages = data.get("webPages", {}).get("value", [])
        
        results = []
        for result in web_pages[:num_results]:
            results.append({
                "title": result.get("name", ""),
                "link": result.get("url", ""),
                "snippet": result.get("snippet", ""),
                "position": len(results) + 1,
                "displayed_link": result.get("displayUrl", ""),
                "source": "bing"
            })
        
        logger.info(f"Found {len(results)} Bing results for: '{query}'")
        return results
        
    except Exception as e:
        logger.error(f"Bing search failed: {str(e)}")
        return []

def search_google_custom(query: str, num_results: int = 10) -> List[Dict[str, Any]]:
    """
    Search using Google Custom Search API
    Free tier: 100 searches/day
    """
    
    google_api_key = settings.GOOGLE_API_KEY
    google_cse_id = settings.GOOGLE_CSE_ID
    
    if not google_api_key or not google_cse_id:
        logger.warning("Google Custom Search not configured")
        return []
    
    try:
        logger.info(f"🔍 Google Custom Search for: '{query}' (limit: {num_results})")
        
        add_rate_limit_delay()
        
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": google_api_key,
            "cx": google_cse_id,
            "q": query,
            "num": min(num_results, 10)  # Google CSE limit is 10 per request
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        items = data.get("items", [])
        
        results = []
        for item in items[:num_results]:
            results.append({
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "position": len(results) + 1,
                "displayed_link": item.get("displayLink", ""),
                "source": "google_cse"
            })
        
        logger.info(f"Found {len(results)} Google Custom Search results for: '{query}'")
        return results
        
    except Exception as e:
        logger.error(f"Google Custom Search failed: {str(e)}")
        return []

def search_google(query: str, num_results: int = 10) -> List[Dict[str, Any]]:
    """
    Main search function that tries multiple free search providers
    """
    
    # Check cache first
    cache_key = f"search_{query}_{num_results}"
    if cache_key in _search_cache:
        cache_time, cached_results = _search_cache[cache_key]
        if time.time() - cache_time < _cache_ttl:
            logger.info(f"⚡ Returning cached search results for: '{query}'")
            return cached_results
        else:
            del _search_cache[cache_key]
    
    logger.info(f"🚀 Multi-provider search for: '{query}' (limit: {num_results})")
    
    # Try providers in order of preference
    providers = [
        ("DuckDuckGo", search_duckduckgo),
        ("Bing", search_bing_web),
        ("Google Custom Search", search_google_custom),
    ]
    
    for provider_name, provider_func in providers:
        try:
            logger.info(f"Trying {provider_name}...")
            results = provider_func(query, num_results)
            
            if results:
                # Cache successful results
                _search_cache[cache_key] = (time.time(), results)
                logger.info(f"✅ {provider_name} returned {len(results)} results")
                return results
                
        except Exception as e:
            logger.warning(f"❌ {provider_name} failed: {str(e)}")
            continue
    
    # If all providers fail, use fallback
    logger.warning(f"All search providers failed for: '{query}', using fallback")
    return create_fallback_search_results(query, num_results)

def search_google_shopping(query: str, num_results: int = 10) -> List[Dict[str, Any]]:
    """
    Shopping search using free alternatives
    """
    
    logger.info(f"🛒 Shopping search for: '{query}' (limit: {num_results})")
    
    # For shopping, we'll use a combination of search and product database
    try:
        # Try to get general search results first
        search_results = search_google(f"{query} product buy", num_results)
        
        # Convert to shopping format
        shopping_results = []
        for result in search_results:
            shopping_result = {
                "title": result["title"],
                "link": result["link"],
                "price": "Price not available",  # Would need price extraction
                "source": "Search Result",
                "thumbnail": "",  # Would need image extraction
                "rating": None,
                "reviews": None,
                "delivery": "Standard shipping",
                "position": result["position"],
                "fallback": True
            }
            shopping_results.append(shopping_result)
        
        return shopping_results
        
    except Exception as e:
        logger.error(f"Shopping search failed: {str(e)}")
        return create_fallback_shopping_results(query, num_results)

def create_fallback_search_results(query: str, num_results: int = 10) -> List[Dict[str, Any]]:
    """
    Create intelligent fallback results using product database
    """
    logger.warning(f"Using fallback product database for query: '{query}'")
    
    # This would use the same product database logic as your current SerpAPI service
    # For now, returning a simple fallback
    return [
        {
            "title": f"Search result for: {query}",
            "link": f"https://duckduckgo.com/?q={quote_plus(query)}",
            "snippet": f"Search results for {query} from DuckDuckGo",
            "position": 1,
            "displayed_link": "duckduckgo.com",
            "fallback": True
        }
    ]

def create_fallback_shopping_results(query: str, num_results: int = 10) -> List[Dict[str, Any]]:
    """
    Create shopping fallback results
    """
    logger.warning(f"Using fallback shopping results for query: '{query}'")
    
    return [
        {
            "title": f"Shopping result for: {query}",
            "link": f"https://duckduckgo.com/?q={quote_plus(query)}&tbm=shop",
            "price": "Price not available",
            "source": "DuckDuckGo Shopping",
            "thumbnail": "",
            "rating": None,
            "reviews": None,
            "delivery": "Standard shipping",
            "position": 1,
            "fallback": True
        }
    ]

def test_search_connection() -> Dict[str, Any]:
    """
    Test search connection with multiple providers
    """
    try:
        # Test DuckDuckGo
        ddg_results = search_duckduckgo("test query", num_results=3)
        
        # Test main search function
        search_results = search_google("test query", num_results=3)
        
        # Test shopping search
        shopping_results = search_google_shopping("laptop", num_results=3)
        
        return {
            "status": "success",
            "duckduckgo_results": len(ddg_results),
            "main_search_results": len(search_results),
            "shopping_search_results": len(shopping_results),
            "providers_configured": {
                "duckduckgo": True,  # Always available
                "bing": bool(settings.BING_API_KEY),
                "google_cse": bool(settings.GOOGLE_API_KEY and settings.GOOGLE_CSE_ID)
            }
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "providers_configured": {
                "duckduckgo": True,
                "bing": bool(settings.BING_API_KEY),
                "google_cse": bool(settings.GOOGLE_API_KEY and settings.GOOGLE_CSE_ID)
            }
        } 