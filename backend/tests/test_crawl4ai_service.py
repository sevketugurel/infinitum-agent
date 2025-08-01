# File: tests/test_crawl4ai_service.py
import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock
from infinitum.services.crawl4ai_service import (
    get_structured_data, 
    get_structured_data_sync, 
    _clean_product_data,
    _fallback_extraction
)


class TestCrawl4AIService:
    """Unit tests for Crawl4AI service."""
    
    def test_clean_product_data_with_valid_data(self):
        """Test _clean_product_data with valid input."""
        input_data = {
            "title": "Sony WH-1000XM5 Headphones",
            "price": "$349.99",
            "brand": "Sony",
            "image": "https://example.com/image.jpg",
            "description": "Great headphones with noise canceling",
            "url": "https://example.com/product",
            "extraction_method": "crawl4ai"
        }
        
        result = _clean_product_data(input_data)
        
        assert result["title"] == "Sony WH-1000XM5 Headphones"
        assert result["price"] == "$349.99"
        assert result["brand"] == "Sony"
        assert result["image"] == "https://example.com/image.jpg"
        assert result["description"] == "Great headphones with noise canceling"
        assert result["url"] == "https://example.com/product"
        assert result["extraction_method"] == "crawl4ai"
    
    def test_clean_product_data_with_null_values(self):
        """Test _clean_product_data with null/empty values."""
        input_data = {
            "title": "null",
            "price": "none",
            "brand": "",
            "image": "null",
            "description": None,
            "url": "https://example.com/product"
        }
        
        result = _clean_product_data(input_data)
        
        assert result["title"] == "Product title not found"
        assert result["price"] is None
        assert result["brand"] is None
        assert result["image"] is None
        assert result["description"] is None
    
    def test_clean_product_data_with_long_description(self):
        """Test _clean_product_data with long description."""
        long_desc = "This is a very long description that should be truncated. " * 10
        input_data = {
            "title": "Test Product",
            "description": long_desc,
            "url": "https://example.com/product"
        }
        
        result = _clean_product_data(input_data)
        
        assert len(result["description"]) <= 203  # 200 + "..."
        assert result["description"].endswith("...")
    
    def test_clean_product_data_with_invalid_image_url(self):
        """Test _clean_product_data with invalid image URL."""
        input_data = {
            "title": "Test Product",
            "image": "not-a-url",
            "url": "https://example.com/product"
        }
        
        result = _clean_product_data(input_data)
        
        assert result["image"] is None
    
    @patch('app.services.crawl4ai_service.AsyncWebCrawler')
    @patch('app.services.crawl4ai_service.ask_gemini')
    async def test_get_structured_data_success(self, mock_ask_gemini, mock_crawler_class):
        """Test successful get_structured_data call."""
        # Mock the crawler
        mock_crawler = AsyncMock()
        mock_crawler_class.return_value.__aenter__.return_value = mock_crawler
        
        # Mock successful result
        mock_result = Mock()
        mock_result.success = True
        mock_result.extracted_content = json.dumps({
            "title": "Test Product",
            "price": "$99.99",
            "brand": "TestBrand"
        })
        mock_crawler.arun.return_value = mock_result
        
        result = await get_structured_data("https://example.com/product")
        
        assert result["title"] == "Test Product"
        assert result["price"] == "$99.99"
        assert result["brand"] == "TestBrand"
        assert result["url"] == "https://example.com/product"
        assert result["extraction_method"] == "crawl4ai_with_gemini"
    
    @patch('app.services.crawl4ai_service.AsyncWebCrawler')
    async def test_get_structured_data_crawler_failure(self, mock_crawler_class):
        """Test get_structured_data when crawler fails."""
        # Mock the crawler
        mock_crawler = AsyncMock()
        mock_crawler_class.return_value.__aenter__.return_value = mock_crawler
        
        # Mock failed result
        mock_result = Mock()
        mock_result.success = False
        mock_result.error_message = "Connection failed"
        mock_crawler.arun.return_value = mock_result
        
        with patch('app.services.crawl4ai_service._fallback_extraction') as mock_fallback:
            mock_fallback.return_value = {"title": "Fallback result"}
            
            result = await get_structured_data("https://example.com/product")
            
            # Should call fallback
            mock_fallback.assert_called_once()
    
    @patch('app.services.crawl4ai_service.AsyncWebCrawler')
    async def test_get_structured_data_json_parse_error(self, mock_crawler_class):
        """Test get_structured_data when JSON parsing fails."""
        # Mock the crawler
        mock_crawler = AsyncMock()
        mock_crawler_class.return_value.__aenter__.return_value = mock_crawler
        
        # Mock result with invalid JSON
        mock_result = Mock()
        mock_result.success = True
        mock_result.extracted_content = "invalid json content"
        mock_result.cleaned_html = "<html>test</html>"
        mock_crawler.arun.return_value = mock_result
        
        with patch('app.services.crawl4ai_service._fallback_extraction') as mock_fallback:
            mock_fallback.return_value = {"title": "Fallback result"}
            
            result = await get_structured_data("https://example.com/product")
            
            # Should call fallback with HTML content
            mock_fallback.assert_called_once_with("https://example.com/product", "<html>test</html>")
    
    def test_get_structured_data_sync(self):
        """Test the synchronous wrapper function."""
        with patch('app.services.crawl4ai_service.get_structured_data') as mock_async:
            mock_async.return_value = {"title": "Test Product"}
            
            # Mock asyncio.get_event_loop to simulate no existing loop
            with patch('asyncio.get_event_loop', side_effect=RuntimeError("No event loop")):
                with patch('asyncio.new_event_loop') as mock_new_loop:
                    with patch('asyncio.set_event_loop'):
                        mock_loop = Mock()
                        mock_new_loop.return_value = mock_loop
                        mock_loop.run_until_complete.return_value = {"title": "Test Product"}
                        
                        result = get_structured_data_sync("https://example.com/product")
                        
                        assert result["title"] == "Test Product"
    
    @patch('app.services.crawl4ai_service.ask_gemini')
    @patch('app.services.crawl4ai_service.AsyncWebCrawler')
    async def test_fallback_extraction_success(self, mock_crawler_class, mock_ask_gemini):
        """Test successful fallback extraction."""
        mock_ask_gemini.return_value = '{"title": "Fallback Product", "price": "$49.99"}'
        
        result = await _fallback_extraction("https://example.com/product", "<html>test content</html>")
        
        assert result["title"] == "Fallback Product"
        assert result["price"] == "$49.99"
        assert result["extraction_method"] == "gemini_fallback"
    
    @patch('app.services.crawl4ai_service.ask_gemini')
    async def test_fallback_extraction_gemini_failure(self, mock_ask_gemini):
        """Test fallback extraction when Gemini fails."""
        mock_ask_gemini.side_effect = Exception("Gemini API error")
        
        result = await _fallback_extraction("https://example.com/product")
        
        assert result["title"] == "Extraction failed"
        assert result["extraction_method"] == "fallback_failed"
        assert "error" in result
    
    @patch('app.services.crawl4ai_service.ask_gemini')
    async def test_fallback_extraction_invalid_json_response(self, mock_ask_gemini):
        """Test fallback extraction when Gemini returns invalid JSON."""
        mock_ask_gemini.return_value = "This is not JSON content"
        
        result = await _fallback_extraction("https://example.com/product", "<html>test</html>")
        
        assert result["title"] == "Product title not found"
        assert result["extraction_method"] == "fallback_failed"
        assert "error" in result


class TestErrorHandling:
    """Test error handling scenarios."""
    
    @patch('app.services.crawl4ai_service.AsyncWebCrawler')
    async def test_crawler_exception(self, mock_crawler_class):
        """Test when crawler raises an exception."""
        mock_crawler_class.side_effect = Exception("Crawler initialization failed")
        
        with patch('app.services.crawl4ai_service._fallback_extraction') as mock_fallback:
            mock_fallback.return_value = {"title": "Error fallback"}
            
            result = await get_structured_data("https://example.com/product")
            
            # Should call fallback
            mock_fallback.assert_called_once()
    
    def test_various_url_formats(self):
        """Test URL handling with different formats."""
        test_urls = [
            "https://www.amazon.com/dp/B123456789",
            "http://example.com/product/123",
            "https://store.example.com/category/product-name",
        ]
        
        for url in test_urls:
            data = {"title": "Test", "url": url}
            result = _clean_product_data(data)
            assert result["url"] == url


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 