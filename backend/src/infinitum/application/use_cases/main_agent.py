# File: src/infinitum/application/use_cases/main_agent.py
"""
Main Agent Orchestration Logic for Day 3
Implements the 5-step agent workflow:
1. Gemini interprets user query → search keywords
2. Use SerpAPI for search
3. Gemini filters for product targets
4. Call get_structured_data(url) for metadata
5. Gemini curates JSON bundle
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from infinitum.infrastructure.external_services.vertex_ai import ask_gemini
from infinitum.infrastructure.external_services.crawl4ai_service import get_structured_data
from infinitum.infrastructure.external_services.serpapi_service import search_google, search_google_shopping
from infinitum.infrastructure.external_services.user_context_service import user_context_manager
from infinitum.infrastructure.external_services.semantic_search_service import semantic_search_service
from infinitum.infrastructure.external_services.package_templates import package_template_service
from infinitum.infrastructure.persistence.firestore_client import db, save_product_snapshot
import uuid

# Import structured logging
from infinitum.infrastructure.logging_config import get_agent_logger, log_agent_step, PerformanceTimer
logger = get_agent_logger("orchestration")

class AgentSession:
    """Represents a session with the AI agent"""
    
    def __init__(self, user_query: str, metadata: Dict[str, Any] = None):
        self.session_id = str(uuid.uuid4())
        self.user_query = user_query
        self.metadata = metadata or {}
        self.start_time = datetime.now()
        self.steps_completed = []
        self.search_results = []
        self.filtered_products = []
        self.final_products = []
        
    def log_step(self, step_number: int, step_name: str, result: Any, error: str = None):
        """Log a completed step"""
        step_log = {
            "step_number": step_number,
            "step_name": step_name,
            "timestamp": datetime.now().isoformat(),
            "success": error is None,
            "error": error,
            "result_summary": str(result)[:200] if result else None
        }
        self.steps_completed.append(step_log)
        
        # Use structured logging
        log_agent_step(
            logger=logger,
            step_number=step_number,
            step_name=step_name,
            session_id=self.session_id,
            user_query=self.user_query,
            success=error is None,
            error=error
        )

async def process_user_query(user_query: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Enhanced main agent orchestration function with user context integration.
    
    Args:
        user_query (str): The user's product search query
        metadata (Dict[str, Any]): Additional metadata about the request
        
    Returns:
        Dict[str, Any]: Final curated response with products and session info
    """
    session = AgentSession(user_query, metadata)
    user_id = metadata.get('user_id') if metadata else None
    
    try:
        logger.info(f"Starting agent processing for session {session.session_id}")
        
        # Step 0: Analyze user context and preferences (NEW)
        user_context = None
        if user_id:
            user_context = await user_context_manager.analyze_user_context(user_id, user_query)
            session.user_context = user_context
            logger.info(f"Loaded user context for user: {user_id}")
        
        # Step 1: Enhanced query interpretation with semantic analysis (now includes search keywords)
        semantic_analysis = await semantic_search_service.enhance_query_understanding(user_query, user_context)
        session.semantic_analysis = semantic_analysis
        
        # Extract search keywords from the combined analysis (reducing API calls by 50%)
        search_keywords = semantic_analysis.get("search_keywords", [user_query.strip()])
        if not search_keywords or len(search_keywords) == 0:
            search_keywords = [user_query.strip()]
        
        session.log_step(1, "extract_search_keywords", search_keywords)  # SUCCESS - no error message
        
        # Step 2: Use SerpAPI for search
        search_results = await step_2_search_google(session, search_keywords)
        
        # Step 3: Filter and prioritize e-commerce URLs for product extraction
        filtered_urls = await step_3_filter_product_targets(session, search_results, user_query)
        
        # Step 4: Extract comprehensive product data from prioritized URLs
        product_data = await step_4_extract_product_data(session, filtered_urls)
        
        # Step 5: Enhanced curation with semantic analysis and templates
        final_response = await step_5_curate_final_response(session, product_data, user_query, user_context, semantic_analysis)
        
        # Save session to Firestore
        await save_session_to_firestore(session, final_response)
        
        # Save conversation to user history (NEW)
        if user_id:
            conversation_id = await user_context_manager.save_conversation(
                user_id, session.session_id, user_query, final_response, 
                {"user_context": user_context, "processing_steps": session.steps_completed}
            )
            final_response["conversation_id"] = conversation_id
        
        logger.info(f"Agent processing completed successfully for session {session.session_id}")
        
        return {
            "session_id": session.session_id,
            "status": "success",
            "user_query": user_query,
            "metadata": metadata,
            "processing_time_seconds": (datetime.now() - session.start_time).total_seconds(),
            "steps_completed": len(session.steps_completed),
            "products_found": len(final_response.get("all_products", final_response.get("products", []))),
            "packages_created": final_response.get("package_count", 0),
            "response": final_response
        }
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Agent processing failed for session {session.session_id}: {error_msg}")
        
        # Save failed session to Firestore for debugging
        await save_session_to_firestore(session, {"error": error_msg})
        
        return {
            "session_id": session.session_id,
            "status": "error",
            "user_query": user_query,
            "error": error_msg,
            "processing_time_seconds": (datetime.now() - session.start_time).total_seconds(),
            "steps_completed": len(session.steps_completed)
        }

async def step_1_extract_search_keywords(session: AgentSession, user_query: str, user_context: Dict[str, Any] = None, semantic_analysis: Dict[str, Any] = None) -> List[str]:
    """Step 1: Enhanced keyword extraction with user context"""
    try:
        # Build enhanced prompt with semantic and context information
        context_info = ""
        if user_context:
            preferences = user_context.get("user_profile", {}).get("preferences", {})
            recent_interests = user_context.get("recent_interests", [])
            
            if preferences.get("budget_conscious"):
                context_info += "User prefers budget-friendly options. "
            if preferences.get("quality_focused"):
                context_info += "User prefers high-quality, premium options. "
            if recent_interests:
                context_info += f"User has recently searched for: {', '.join(recent_interests)}. "
        
        semantic_info = ""
        if semantic_analysis:
            categories = semantic_analysis.get("product_categories", [])
            use_case = semantic_analysis.get("use_case", "")
            alternatives = semantic_analysis.get("alternatives", [])
            
            if categories:
                semantic_info += f"Detected categories: {', '.join(categories)}. "
            if use_case:
                semantic_info += f"Use case: {use_case}. "
            if alternatives:
                semantic_info += f"Alternative terms: {', '.join(alternatives[:3])}. "
        
        prompt = f"""
        Extract the best Google search keywords from this user query for finding products to buy.
        Focus on product names, brands, categories, and specific features mentioned.
        
        User Query: "{user_query}"
        {f"User Context: {context_info}" if context_info else ""}
        {f"Semantic Analysis: {semantic_info}" if semantic_info else ""}
        
        Return a JSON array of 3-5 search keyword strings, prioritized by relevance.
        Each keyword should be 1-4 words long and optimized for product search.
        Consider the user's preferences and context when selecting keywords.
        
        Example: ["wireless headphones", "Sony WH-1000XM5", "noise canceling headphones"]
        
        Return ONLY the JSON array, no other text.
        """
        
        response = ask_gemini(prompt)
        
        # Parse JSON response
        json_start = response.find('[')
        json_end = response.rfind(']') + 1
        if json_start >= 0 and json_end > json_start:
            keywords = json.loads(response[json_start:json_end])
            if isinstance(keywords, list) and len(keywords) > 0:
                session.log_step(1, "extract_search_keywords", keywords)
                return keywords
        
        # Fallback: use original query
        fallback_keywords = [user_query.strip()]
        session.log_step(1, "extract_search_keywords", fallback_keywords, "Failed to parse Gemini response, using fallback")
        return fallback_keywords
        
    except Exception as e:
        error_msg = f"Step 1 failed: {str(e)}"
        session.log_step(1, "extract_search_keywords", None, error_msg)
        # Return fallback keywords to continue processing
        return [user_query.strip()]

async def step_2_search_google(session: AgentSession, keywords: List[str]) -> List[Dict[str, Any]]:
    """Step 2: Enhanced Google search combining Shopping API and organic results"""
    all_results = []
    
    # E-commerce domains to prioritize
    ecommerce_domains = [
        'amazon.com', 'amazon.co.uk', 'amazon.de', 'amazon.fr',
        'ebay.com', 'etsy.com', 'walmart.com', 'target.com',
        'bestbuy.com', 'newegg.com', 'alibaba.com', 'aliexpress.com',
        'shopify.com', 'bigcommerce.com', 'woocommerce.com'
    ]
    
    try:
        for keyword in keywords[:3]:  # Limit to top 3 keywords to avoid hitting API limits
            try:
                # FIRST: Try Google Shopping API for direct product results
                try:
                    shopping_results = search_google_shopping(keyword, num_results=15)
                    if shopping_results:
                        for result in shopping_results:
                            result['search_keyword'] = keyword
                            result['source_type'] = 'shopping'
                            result['is_ecommerce'] = True  # Shopping results are always e-commerce
                            result['is_direct_product'] = True  # Shopping results are direct products
                        all_results.extend(shopping_results)
                        logger.info(f"✅ Found {len(shopping_results)} shopping results for '{keyword}'")
                except Exception as e:
                    logger.warning(f"Google Shopping search failed for '{keyword}': {e}")
                
                # SECOND: Organic search with diverse e-commerce focused queries  
                enhanced_queries = [
                    f"{keyword} buy online",
                    f"{keyword} price store",
                    f'"{keyword}" product page',
                    f"site:amazon.com {keyword}",
                    f"site:ebay.com {keyword}",
                    f"site:walmart.com {keyword}",
                    f"site:bestbuy.com {keyword}",
                    f"site:target.com {keyword}",
                    f"{keyword} purchase",
                    f"{keyword} shop"
                ]
                
                for query in enhanced_queries:
                    regular_res = search_google(query, num_results=8)
                    if regular_res:
                        for result in regular_res:
                            result['search_keyword'] = keyword
                            result['original_query'] = query
                            result['source_type'] = 'organic'
                            
                            # Check if this is an e-commerce site
                            link = result.get('link', '')
                            result['is_ecommerce'] = any(domain in link.lower() for domain in ecommerce_domains)
                            
                            # Try to identify if this is a direct product page vs category page
                            result['is_direct_product'] = _is_likely_product_page(result)
                            
                        all_results.extend(regular_res)
                    
            except Exception as e:
                logger.warning(f"Search failed for keyword '{keyword}': {str(e)}")
                continue
        
        # Sort results: Shopping results first, then direct product pages, then e-commerce sites
        sorted_results = sorted(all_results, key=lambda x: (
            x.get('source_type') != 'shopping',  # Shopping results first
            not x.get('is_direct_product', False),  # Then direct product pages
            not x.get('is_ecommerce', False),  # Then e-commerce sites
            x.get('position', 999)  # Finally by search position
        ))
        
        session.search_results = sorted_results
        shopping_count = sum(1 for r in sorted_results if r.get('source_type') == 'shopping')
        product_count = sum(1 for r in sorted_results if r.get('is_direct_product'))
        ecommerce_count = sum(1 for r in sorted_results if r.get('is_ecommerce'))
        
        session.log_step(2, "search_google", 
                        f"{len(sorted_results)} total results ({shopping_count} shopping, {product_count} direct products, {ecommerce_count} e-commerce)")
        return sorted_results
        
    except Exception as e:
        error_msg = f"Step 2 failed: {str(e)}"
        session.log_step(2, "search_google", None, error_msg)
        return []

def _is_likely_product_page(result: Dict[str, Any]) -> bool:
    """Determine if a search result is likely a direct product page vs category/review page"""
    title = result.get('title', '').lower()
    link = result.get('link', '').lower()
    snippet = result.get('snippet', '').lower()
    
    # EXCLUDE review sites and category pages (BAD)
    exclude_sites = [
        'rtings.com', 'wirecutter.com', 'techradar.com', 'cnet.com',
        'tomsguide.com', 'pcmag.com', 'soundguys.com', 'headphonesty.com'
    ]
    
    category_indicators = [
        'search results', 'category', 'browse', 'shop all', 'collection',
        'noise-cancelling headphones', 'headphones -', '/c/', '/category/',
        'filter', 'sort by', 'see all', 'view all', 'compare', 'best of',
        'top 10', 'review', 'vs ', 'compared', 'buying guide'
    ]
    
    # PREFER actual product pages (GOOD)  
    product_indicators = [
        'buy now', 'add to cart', 'in stock', 'price', '$',
        'model', 'brand new', 'specifications', 'features',
        '/p/', '/dp/', '/product/', '/item/', 'sku:', 'model #'
    ]
    
    # Check for excluded review sites
    for site in exclude_sites:
        if site in link:
            return False
    
    # Check for category page indicators
    for indicator in category_indicators:
        if indicator in title or indicator in link or indicator in snippet:
            return False
    
    # Check for product page indicators
    for indicator in product_indicators:
        if indicator in title or indicator in link or indicator in snippet:
            return True
    
    # Check URL structure - product pages often have specific patterns
    if any(pattern in link for pattern in ['/dp/', '/p/', '/product/', '/item/', '/products/']):
        return True
    
    # Default to False for ambiguous cases
    return False

async def step_3_filter_product_targets(session: AgentSession, search_results: List[Dict[str, Any]], original_query: str) -> List[str]:
    """Step 3: Filter and prioritize URLs for product extraction with improved category page detection"""
    try:
        if not search_results:
            session.log_step(3, "filter_product_targets", [], "No search results to filter")
            return []
        
        # Separate results by type and quality
        shopping_urls = []
        direct_product_urls = []
        ecommerce_urls = []
        other_urls = []
        
        for result in search_results:
            url = result.get('link', '')
            if not url or not url.startswith(('http://', 'https://')):
                continue
                
            # Skip obvious category/search pages
            if _is_category_page(result):
                logger.info(f"🚫 Skipping category page: {result.get('title', '')[:50]}...")
                continue
            
            # Categorize by result type
            if result.get('source_type') == 'shopping':
                shopping_urls.append(url)
            elif result.get('is_direct_product', False):
                direct_product_urls.append(url)
            elif result.get('is_ecommerce', False):
                ecommerce_urls.append(url)
            else:
                other_urls.append(url)
        
        # Build prioritized list: HEAVILY prioritize Shopping results (they have built-in prices!)
        prioritized_urls = []
        prioritized_urls.extend(shopping_urls[:12])  # Top 12 shopping results (massive increase - these have prices!)
        prioritized_urls.extend(direct_product_urls[:4])  # Reduced direct products (often problematic)
        prioritized_urls.extend(ecommerce_urls[:2])  # Reduced other e-commerce (often problematic)
        
        # If still not enough, use Gemini to select from remaining URLs
        if len(prioritized_urls) < 10 and (ecommerce_urls[4:] + other_urls):
            remaining_urls = list(set(ecommerce_urls[4:] + other_urls) - set(prioritized_urls))
            gemini_urls = await _gemini_filter_urls(remaining_urls[:15], search_results, original_query)
            prioritized_urls.extend(gemini_urls[:6])  # Increased from 3
        
        # Remove duplicates while preserving order
        final_urls = []
        seen = set()
        for url in prioritized_urls:
            if url not in seen:
                final_urls.append(url)
                seen.add(url)
        
        logger.info(f"📋 URL prioritization: {len(shopping_urls)} shopping, {len(direct_product_urls)} direct products, {len(ecommerce_urls)} e-commerce")
        session.log_step(3, "filter_product_targets", f"{len(final_urls)} URLs prioritized for extraction")
        return final_urls[:15]  # Increased limit from 8 to 15 URLs
        
    except Exception as e:
        error_msg = f"Step 3 failed: {str(e)}"
        session.log_step(3, "filter_product_targets", None, error_msg)
        return []

def _is_category_page(result: Dict[str, Any]) -> bool:
    """Enhanced detection of category/search pages to exclude"""
    title = result.get('title', '').lower()
    link = result.get('link', '').lower()
    snippet = result.get('snippet', '').lower()
    
    # Strong indicators this is a category page (should be excluded)
    category_indicators = [
        # Explicit category terms
        'category', 'categories', 'browse', 'shop all', 'see all', 'view all',
        'collection', 'collections', 'department', 'departments',
        
        # Search/filter terms  
        'search results', 'results for', 'filter by', 'sort by', 'refine',
        'narrow your search', 'search within',
        
        # Generic product listing terms
        'noise-cancelling headphones', 'headphones -', 'headphones |',
        'wireless headphones', 'bluetooth headphones',
        
        # URL patterns for categories
        '/c/', '/category/', '/categories/', '/browse/', '/search/',
        '/shop/', '/all-', '/department/', '/collections/'
    ]
    
    # Check title for category indicators
    for indicator in category_indicators:
        if indicator in title:
            return True
    
    # Check URL for category patterns
    for indicator in category_indicators:
        if indicator in link:
            return True
    
    # Check snippet for category language
    category_snippet_terms = [
        'discover a wide range', 'explore our selection', 'shop for',
        'find the perfect', 'browse our', 'choose from'
    ]
    
    for term in category_snippet_terms:
        if term in snippet:
            return True
    
    return False

async def _gemini_filter_urls(urls: List[str], search_results: List[Dict[str, Any]], original_query: str) -> List[str]:
    """Use Gemini to filter remaining URLs"""
    try:
        if not urls:
            return []
            
        results_text = ""
        for i, url in enumerate(urls):
            original_result = next((r for r in search_results if r.get('link') == url), {})
            title = original_result.get('title', 'No title')
            snippet = original_result.get('snippet', '')[:100]
            results_text += f"{i+1}. {title}\n   URL: {url}\n   Snippet: {snippet}\n\n"
        
        prompt = f"""
        Filter these URLs to find ONLY direct product pages that match this query: "{original_query}"
        
        EXCLUDE any pages that are:
        - Category pages or product listings  
        - Search result pages
        - General store pages
        
        INCLUDE only pages that are:
        - Individual product pages with specific products
        - Product detail pages with prices and descriptions
        
        URLs to evaluate:
        {results_text}
        
        Return a JSON array of the best 2-3 product page URLs.
        Return ONLY the JSON array, no other text.
        """
        
        response = ask_gemini(prompt)
        json_start = response.find('[')
        json_end = response.rfind(']') + 1
        if json_start >= 0 and json_end > json_start:
            urls = json.loads(response[json_start:json_end])
            if isinstance(urls, list):
                return [url for url in urls if isinstance(url, str) and url.startswith(('http://', 'https://'))]
        
    except Exception as e:
        logger.warning(f"Gemini URL filtering failed: {e}")
    
    return []

async def step_4_extract_product_data(session: AgentSession, urls: List[str]) -> List[Dict[str, Any]]:
    """Step 4: Extract comprehensive product data from prioritized URLs"""
    all_products = []
    successful_extractions = 0
    
    try:
        # Extract data from prioritized URLs with enhanced processing
        for i, url in enumerate(urls[:12]):  # Increased limit to top 12 URLs
            try:
                logger.info(f"Extracting data from URL {i+1}/{len(urls[:12])}: {url}")
                data = await get_structured_data(url)
                
                if data and data.get('title') and data['title'] not in ["Product title not found", "Extraction failed"]:
                    # Enhanced data cleaning and validation
                    cleaned_data = _enhance_product_data(data, url)
                    
                    # Save individual product to Firestore
                    try:
                        doc_id = save_product_snapshot(cleaned_data)
                        if doc_id:
                            cleaned_data['firestore_id'] = doc_id
                    except Exception as firestore_error:
                        logger.warning(f"Failed to save to Firestore: {firestore_error}")
                        # Continue without Firestore ID
                    
                    all_products.append(cleaned_data)
                    successful_extractions += 1
                    logger.info(f"✅ Successfully extracted: {cleaned_data.get('title', 'Unknown')[:50]}...")
                else:
                    logger.warning(f"❌ Failed to extract valid data from: {url}")
                    
            except Exception as e:
                logger.warning(f"❌ Failed to extract data from {url}: {str(e)}")
                continue
        
        # If we got very few results, add a basic fallback
        if len(all_products) < 3 and len(urls) > 0:
            logger.info("Low extraction success rate, attempting fallback extraction...")
            await _add_fallback_products(session, urls, all_products)
        
        session.final_products = all_products
        session.log_step(4, "extract_product_data", f"{successful_extractions}/{len(urls[:12])} successful extractions = {len(all_products)} total products")
        return all_products
        
    except Exception as e:
        error_msg = f"Step 4 failed: {str(e)}"
        session.log_step(4, "extract_product_data", None, error_msg)
        return all_products  # Return whatever we managed to extract

def _enhance_product_data(data: Dict[str, Any], url: str) -> Dict[str, Any]:
    """Enhance and clean extracted product data"""
    enhanced = data.copy()
    
    # Enhance title if it's too generic
    title = enhanced.get('title', '')
    if len(title) < 10 or title.lower() in ['product', 'item', 'buy']:
        # Try to extract title from URL
        url_parts = url.split('/')
        for part in url_parts:
            if len(part) > 10 and '-' in part:
                enhanced['title'] = part.replace('-', ' ').title()
                break
    
    # Ensure price format
    price = enhanced.get('price')
    if price and isinstance(price, str):
        # Clean up price format
        if not price.startswith(('$', '€', '£', '¥')):
            enhanced['price'] = f"${price}"
    
    # Add URL domain as brand if brand is missing
    if not enhanced.get('brand'):
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            if domain.startswith('www.'):
                domain = domain[4:]
            enhanced['brand'] = domain.split('.')[0].title()
        except:
            pass
    
    # Add extraction timestamp
    from datetime import datetime
    enhanced['extracted_at'] = datetime.now().isoformat()
    
    return enhanced

async def _add_fallback_products(session: AgentSession, urls: List[str], existing_products: List[Dict[str, Any]]) -> None:
    """Add fallback products using our comprehensive real product database"""
    try:
        from .services.serpapi_service import create_fallback_search_results
        
        # Get the original query from session - use the actual user query instead of hardcoded fallback
        original_query = getattr(session, 'query', getattr(session, 'user_query', "general products"))
        
        # Use our real product database to get comprehensive results
        logger.info(f"🚀 Using comprehensive product database for: '{original_query}'")
        fallback_products = create_fallback_search_results(original_query, num_results=15)
        
        # Convert to the format expected by the main agent
        for product in fallback_products:
            if product.get('link') in [p.get('url') for p in existing_products]:
                continue  # Skip already extracted URLs
                
            # Create product with real data from our database
            enhanced_product = {
                'title': product.get('title', 'Product'),
                'price': product.get('price', 'Price not available'),
                'brand': product.get('brand', 'Unknown brand'),
                'description': product.get('snippet', 'No description available'),
                'url': product.get('link', ''),
                'image': None,
                'extraction_method': 'real_product_database',
                'note': 'Real product from comprehensive database with actual Amazon URLs and prices.',
                'rating': product.get('rating', 4.0),
                'reviews': product.get('reviews', 100)
            }
            
            existing_products.append(enhanced_product)
            logger.info(f"📦 Added real product: {enhanced_product['title'][:40]}... - {enhanced_product['price']}")
            
        logger.info(f"✅ Added {len(fallback_products)} real products from comprehensive database")
            
    except Exception as e:
        logger.warning(f"Failed to add real products from database: {e}")
        # Fallback to original method if our database fails
        try:
            search_results = session.search_results if hasattr(session, 'search_results') else []
            
            for result in search_results[:3]:
                if result.get('link') in [p.get('url') for p in existing_products]:
                    continue
                    
                fallback_product = {
                    'title': result.get('title', 'Product'),
                    'price': 'Price not available',
                    'brand': 'Unknown',
                    'description': result.get('snippet', 'No description')[:200],
                    'url': result.get('link', ''),
                    'image': None,
                    'extraction_method': 'fallback_from_search'
                }
                
                existing_products.append(fallback_product)
                logger.info(f"📋 Added search fallback: {fallback_product['title'][:30]}...")
        except Exception as e2:
            logger.error(f"Both real database and search fallback failed: {e2}")

async def step_5_curate_final_response(session: AgentSession, products: List[Dict[str, Any]], original_query: str, user_context: Dict[str, Any] = None, semantic_analysis: Dict[str, Any] = None) -> Dict[str, Any]:
    """Step 5: Use Gemini to curate intelligent shopping packages"""
    try:
        if not products:
            # Try to provide at least basic search results as fallback
            search_results = session.search_results if hasattr(session, 'search_results') else []
            fallback_products = []
            
            # Convert search results to basic product format as last resort
            for result in search_results[:3]:
                if result.get('source_type') == 'shopping':
                    # Already in good format from shopping results
                    fallback_product = {
                        'title': result.get('title', 'Product'),
                        'price': result.get('price', 'Fiyat bilgisi yok'),
                        'brand': result.get('source', 'Marka bilinmiyor'),
                        'url': result.get('link', ''),
                        'description': 'Bu Google Shopping sonucundan alınmıştır.',
                        'extraction_method': 'fallback_shopping'
                    }
                    fallback_products.append(fallback_product)
                elif result.get('link') and result.get('title'):
                    # Convert organic result to basic product format
                    fallback_product = {
                        'title': result.get('title', 'Ürün'),
                        'price': 'Fiyat bilgisi bulunamamıştır',
                        'brand': 'Marka bilinmiyor',
                        'url': result.get('link', ''),
                        'description': result.get('snippet', 'Açıklama bulunamamıştır.')[:150] + "...",
                        'extraction_method': 'fallback_organic'
                    }
                    fallback_products.append(fallback_product)
            
            if fallback_products:
                session.log_step(5, "curate_final_response", {"products": fallback_products, "message": "Fallback products provided"})
                return {
                    "products": fallback_products,
                    "message": f"Sorgunuz için detaylı ürün bilgisi çıkarılamadı, ancak {len(fallback_products)} adet temel sonuç bulundu. Daha detaylı bilgi için ürün linklerini ziyaret edebilirsiniz.",
                    "suggestions": ["Daha spesifik anahtar kelimeler kullanın", "Yazımı kontrol edin", "Farklı ürün kategorileri deneyin"],
                    "total_found": len(fallback_products),
                    "note": "Bu sonuçlar temel arama sonuçlarından oluşturulmuştur."
                }
            
            session.log_step(5, "curate_final_response", {"products": [], "message": "No products found"})
            return {
                "products": [],
                "message": "Sorgunuz için hiç ürün bulunamadı. Lütfen farklı bir arama terimi deneyin.",
                "suggestions": ["Daha spesifik anahtar kelimeler kullanın", "Yazımı kontrol edin", "Farklı ürün kategorileri deneyin"],
                "total_found": 0
            }
        
        # Create intelligent shopping packages using advanced curation
        curated_response = await _create_intelligent_packages(products, original_query, user_context, semantic_analysis)
        session.log_step(5, "curate_final_response", "Successfully created intelligent packages")
        return curated_response
        
    except Exception as e:
        error_msg = f"Step 5 failed: {str(e)}"
        session.log_step(5, "curate_final_response", None, error_msg)
        # Return basic fallback
        return {
            "products": products,
            "summary": f"Found {len(products)} products for your search.",
            "total_found": len(products),
            "error": "Failed to curate response"
        }

async def _create_intelligent_packages(products: List[Dict[str, Any]], original_query: str, user_context: Dict[str, Any] = None, semantic_analysis: Dict[str, Any] = None) -> Dict[str, Any]:
    """Create intelligent shopping packages with AI-driven curation and semantic analysis"""
    
    # Apply semantic scoring to products
    if semantic_analysis:
        products = await semantic_search_service.find_similar_products(semantic_analysis, products)
    
    # Check for template-based packages
    template_packages = []
    if semantic_analysis:
        template = package_template_service.get_template_for_query(semantic_analysis)
        if template:
            budget_preference = "budget" if user_context and user_context.get("spending_patterns", {}).get("budget_conscious", 0) > 0 else "balanced"
            template_packages = package_template_service.create_template_based_packages(template, products, budget_preference)
    
    # Prepare products data for Gemini analysis
    products_text = ""
    for i, product in enumerate(products):
        products_text += f"""
Product {i+1}:
- Title: {product.get('title', 'N/A')}
- Price: {product.get('price', 'N/A')}
- Brand: {product.get('brand', 'N/A')}
- Description: {product.get('description', 'N/A')}
- URL: {product.get('url', 'N/A')}
"""
    
    # Build user context information
    context_info = ""
    if user_context:
        preferences = user_context.get("user_profile", {}).get("preferences", {})
        recent_interests = user_context.get("recent_interests", [])
        spending_patterns = user_context.get("spending_patterns", {})
        personalization = user_context.get("personalization_suggestions", [])
        
        context_info = f"""
        USER CONTEXT:
        - Budget conscious: {preferences.get('budget_conscious', False)}
        - Quality focused: {preferences.get('quality_focused', False)}
        - Recent interests: {', '.join(recent_interests) if recent_interests else 'None'}
        - Spending pattern: {'Budget-focused' if spending_patterns.get('budget_conscious', 0) > spending_patterns.get('premium_focused', 0) else 'Quality-focused'}
        - Personalization tips: {'; '.join(personalization) if personalization else 'None'}
        """

    prompt = f"""
    You are an expert shopping assistant creating intelligent, curated shopping packages for this user query: "{original_query}"
    
    {context_info}
    
    Analyze these products and create MULTIPLE intelligent shopping packages that perfectly match different user needs and budgets:
    
    {products_text}
    
    Create a JSON response with these intelligent package categories:

    1. **"packages"** - An array of 3-4 different shopping packages:
       - "economy_package": Best value/budget-friendly options
       - "balanced_package": Best price-performance ratio
       - "premium_package": High-quality, feature-rich options  
       - "complete_setup_package": Everything needed for the use case (if applicable)
    
    2. For each package, include:
       - "name": Package display name (e.g., "Budget-Friendly YouTube Setup")
       - "description": Why this package is recommended (2-3 sentences)
       - "total_estimated_price": Combined estimated price range
       - "products": Array of products in this package with relevance_score (1-10)
       - "why_this_package": Specific benefits and use cases
       
    3. **"summary"**: Overall analysis of what was found and package strategy
    4. **"expert_recommendations"**: 3-4 actionable buying tips specific to this query
    5. **"all_products"**: All products sorted by overall relevance
    6. **"total_found"**: Total number of products

    CRITICAL REQUIREMENTS:
    - Create packages that tell a STORY - why someone would choose each option
    - Include price analysis when available
    - Make packages ACTIONABLE - users should be able to buy immediately
    - Be specific about what makes each package special
    - Focus on USER VALUE and REAL BENEFITS
    
    Return ONLY the JSON object, no other text.
    """
    
    try:
        response = ask_gemini(prompt)
        
        # Parse JSON response
        json_start = response.find('{')
        json_end = response.rfind('}') + 1
        if json_start >= 0 and json_end > json_start:
            curated_response = json.loads(response[json_start:json_end])
            if isinstance(curated_response, dict):
                # Enhance the response with metadata and semantic analysis
                curated_response["query_analysis"] = _analyze_query_intent(original_query)
                curated_response["semantic_analysis"] = semantic_analysis
                curated_response["package_count"] = len(curated_response.get("packages", []))
                
                # Add semantic suggestions
                if semantic_analysis:
                    curated_response["semantic_suggestions"] = await semantic_search_service.generate_semantic_suggestions(semantic_analysis, user_context)
                
                # Add template packages if available
                if template_packages:
                    curated_response["template_packages"] = template_packages
                    if "packages" in curated_response:
                        curated_response["packages"].extend(template_packages)
                
                # Enhance packages with semantic scoring
                if semantic_analysis and curated_response.get("packages"):
                    curated_response["packages"] = await semantic_search_service.enhance_product_packages(
                        curated_response["packages"], semantic_analysis
                    )
                
                return curated_response
        
        # Fallback: create basic packages programmatically
        fallback_response = _create_fallback_packages(products, original_query)
        
        # Add template packages if available
        if template_packages:
            fallback_response["template_packages"] = template_packages
            fallback_response["packages"].extend(template_packages)
        
        return fallback_response
        
    except Exception as e:
        logger.warning(f"Failed to create intelligent packages: {e}")
        return _create_fallback_packages(products, original_query)

def _analyze_query_intent(query: str) -> Dict[str, Any]:
    """Analyze user query to understand intent and context"""
    query_lower = query.lower()
    
    intent_analysis = {
        "category": "general",
        "budget_conscious": False,
        "quality_focused": False,
        "setup_type": "single_item",
        "urgency": "normal"
    }
    
    # Budget indicators
    if any(word in query_lower for word in ["economical", "budget", "cheap", "affordable", "under", "below"]):
        intent_analysis["budget_conscious"] = True
        
    # Quality indicators  
    if any(word in query_lower for word in ["premium", "high-quality", "professional", "best", "top"]):
        intent_analysis["quality_focused"] = True
        
    # Setup type detection
    if any(word in query_lower for word in ["setup", "kit", "complete", "system", "bundle"]):
        intent_analysis["setup_type"] = "complete_setup"
        
    # Category detection
    if any(word in query_lower for word in ["youtube", "streaming", "content"]):
        intent_analysis["category"] = "content_creation"
    elif any(word in query_lower for word in ["gaming", "game", "gamer"]):
        intent_analysis["category"] = "gaming"
    elif any(word in query_lower for word in ["office", "work", "business"]):
        intent_analysis["category"] = "professional"
    elif any(word in query_lower for word in ["home", "smart", "automation"]):
        intent_analysis["category"] = "smart_home"
        
    return intent_analysis

def _create_fallback_packages(products: List[Dict[str, Any]], original_query: str) -> Dict[str, Any]:
    """Create basic packages when AI curation fails"""
    
    # Sort products by estimated price (if available)
    products_with_prices = []
    products_without_prices = []
    
    for product in products:
        price_str = product.get('price', '')
        if price_str and any(char.isdigit() for char in price_str):
            products_with_prices.append(product)
        else:
            products_without_prices.append(product)
    
    # Create basic packages
    packages = []
    
    # Economy package - first few products
    if len(products) >= 1:
        packages.append({
            "name": "Budget Option",
            "description": "Most affordable options that meet your needs.",
            "total_estimated_price": "Budget-friendly range",
            "products": products[:2],
            "why_this_package": "Best value for money while meeting basic requirements."
        })
    
    # Balanced package - middle products
    if len(products) >= 3:
        packages.append({
            "name": "Balanced Choice", 
            "description": "Good balance of features and price.",
            "total_estimated_price": "Mid-range options",
            "products": products[1:4],
            "why_this_package": "Optimal balance between quality and affordability."
        })
    
    # Premium package - top products
    if len(products) >= 2:
        packages.append({
            "name": "Premium Selection",
            "description": "High-quality options with the best features.",
            "total_estimated_price": "Higher-end range", 
            "products": products[-2:],
            "why_this_package": "Top-tier quality and features for the best experience."
        })
    
    return {
        "packages": packages,
        "summary": f"Found {len(products)} products and organized them into {len(packages)} curated packages for '{original_query}'",
        "expert_recommendations": [
            "Compare specifications carefully before purchasing",
            "Check user reviews and ratings",
            "Verify return policies and warranties",
            "Consider your specific use case and budget"
        ],
        "all_products": products,
        "total_found": len(products),
        "package_count": len(packages),
        "query_analysis": _analyze_query_intent(original_query)
    }

async def save_session_to_firestore(session: AgentSession, final_response: Dict[str, Any]):
    """Save the complete session data to Firestore"""
    try:
        session_data = {
            "session_id": session.session_id,
            "user_query": session.user_query,
            "metadata": session.metadata,
            "start_time": session.start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
            "processing_time_seconds": (datetime.now() - session.start_time).total_seconds(),
            "steps_completed": session.steps_completed,
            "search_results_count": len(session.search_results),
            "filtered_products_count": len(session.filtered_products),
            "final_products_count": len(session.final_products),
            "final_response": final_response,
            "success": final_response.get("error") is None
        }
        
        # Save to Firestore sessions collection
        sessions_ref = db.collection('sessions')
        sessions_ref.document(session.session_id).set(session_data)
        
        logger.info(f"Session {session.session_id} saved to Firestore")
        
    except Exception as e:
        logger.error(f"Failed to save session to Firestore: {str(e)}")