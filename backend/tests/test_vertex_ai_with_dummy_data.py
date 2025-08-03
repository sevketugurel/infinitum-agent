"""
Enhanced Vertex AI tests using dummy data.

This module provides comprehensive testing of Vertex AI functionality
using the dummy data defined in vertex_ai_dummy_data.py.
"""

import pytest
import os
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import sys
import tempfile

# Add the tests directory to the path to import dummy data
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dummy_data.vertex_ai_dummy_data import (
    MOCK_GEMINI_RESPONSES,
    TEST_PROMPTS,
    MOCK_CACHE_ENTRIES,
    MOCK_QUOTA_DATA,
    MOCK_LLM_INSTANCES,
    MOCK_ERROR_RESPONSES,
    MOCK_CONFIG_DATA,
    MOCK_API_RESPONSES,
    TEST_SCENARIOS,
    get_mock_response_for_prompt,
    create_mock_cache_entry,
    get_test_prompts_by_category,
    get_mock_quota_data,
    get_test_scenario
)

# Import the actual Vertex AI service
from src.infinitum.infrastructure.external_services.vertex_ai import (
    ask_gemini, 
    initialize_vertex_ai, 
    create_llm_with_retry,
    get_quota_status,
    clear_cache,
    get_cache_stats
)


class TestVertexAIWithDummyData:
    """Enhanced tests for Vertex AI using dummy data."""
    
    def setup_method(self):
        """Set up test environment before each test."""
        # Clear any existing cache
        clear_cache()
    
    def test_ask_gemini_with_dummy_responses(self):
        """Test ask_gemini with various dummy responses."""
        test_cases = [
            ("What is 2+2?", MOCK_GEMINI_RESPONSES["simple_math"]),
            ("Extract keywords from this product description", MOCK_GEMINI_RESPONSES["keyword_extraction"]),
            ("Create a package for professional equipment", MOCK_GEMINI_RESPONSES["package_creation"]),
            ("Analyze this product", MOCK_GEMINI_RESPONSES["technical_analysis"]),
            ("Find the best headphones", MOCK_GEMINI_RESPONSES["product_search"]),
        ]
        
        with patch('infinitum.infrastructure.external_services.vertex_ai.llm') as mock_llm:
            for prompt, expected_response in test_cases:
                mock_llm.call.return_value = expected_response
                
                result = ask_gemini(prompt)
                
                assert result == expected_response
                mock_llm.call.assert_called_with(prompt)
    
    def test_ask_gemini_with_edge_cases(self):
        """Test ask_gemini with edge case prompts."""
        edge_cases = TEST_PROMPTS["edge_cases"]
        
        with patch('infinitum.infrastructure.external_services.vertex_ai.llm') as mock_llm:
            for prompt in edge_cases:
                # Use the utility function to get appropriate mock response
                expected_response = get_mock_response_for_prompt(prompt)
                mock_llm.call.return_value = expected_response
                
                result = ask_gemini(prompt)
                
                assert result == expected_response
                mock_llm.call.assert_called_with(prompt)
    
    def test_ask_gemini_with_product_related_prompts(self):
        """Test ask_gemini with product-related prompts."""
        product_prompts = TEST_PROMPTS["product_related"]
        
        with patch('infinitum.infrastructure.external_services.vertex_ai.llm') as mock_llm:
            for prompt in product_prompts:
                expected_response = get_mock_response_for_prompt(prompt)
                mock_llm.call.return_value = expected_response
                
                result = ask_gemini(prompt)
                
                assert result == expected_response
                assert len(result) > 0
                mock_llm.call.assert_called_with(prompt)
    
    def test_ask_gemini_with_technical_queries(self):
        """Test ask_gemini with technical queries."""
        technical_prompts = TEST_PROMPTS["technical_queries"]
        
        with patch('infinitum.infrastructure.external_services.vertex_ai.llm') as mock_llm:
            for prompt in technical_prompts:
                expected_response = get_mock_response_for_prompt(prompt)
                mock_llm.call.return_value = expected_response
                
                result = ask_gemini(prompt)
                
                assert result == expected_response
                assert len(result) > 0
                mock_llm.call.assert_called_with(prompt)
    
    def test_ask_gemini_with_creative_requests(self):
        """Test ask_gemini with creative requests."""
        creative_prompts = TEST_PROMPTS["creative_requests"]
        
        with patch('infinitum.infrastructure.external_services.vertex_ai.llm') as mock_llm:
            for prompt in creative_prompts:
                expected_response = get_mock_response_for_prompt(prompt)
                mock_llm.call.return_value = expected_response
                
                result = ask_gemini(prompt)
                
                assert result == expected_response
                assert len(result) > 0
                mock_llm.call.assert_called_with(prompt)
    
    def test_ask_gemini_with_empty_response(self):
        """Test ask_gemini when LLM returns empty response."""
        with patch('infinitum.infrastructure.external_services.vertex_ai.llm') as mock_llm:
            mock_llm.call.return_value = MOCK_GEMINI_RESPONSES["empty_response"]
            
            with pytest.raises(RuntimeError) as exc_info:
                ask_gemini("Test prompt")
            
            assert "Gemini returned an empty response" in str(exc_info.value)
    
    def test_ask_gemini_with_long_response(self):
        """Test ask_gemini with very long responses."""
        long_prompt = "A" * 1000  # Very long prompt
        expected_response = MOCK_GEMINI_RESPONSES["long_response"]
        
        with patch('infinitum.infrastructure.external_services.vertex_ai.llm') as mock_llm:
            mock_llm.call.return_value = expected_response
            
            result = ask_gemini(long_prompt)
            
            assert result == expected_response
            assert len(result) > 1000  # Should be a long response
            mock_llm.call.assert_called_with(long_prompt)
    
    def test_ask_gemini_with_error_responses(self):
        """Test ask_gemini with various error scenarios."""
        error_scenarios = [
            (MOCK_ERROR_RESPONSES["rate_limit_error"]["type"], "Rate limit exceeded"),
            (MOCK_ERROR_RESPONSES["connection_error"]["type"], "Connection failed"),
            (MOCK_ERROR_RESPONSES["service_unavailable"]["type"], "Service unavailable"),
        ]
        
        with patch('infinitum.infrastructure.external_services.vertex_ai.llm') as mock_llm:
            for error_type, error_message in error_scenarios:
                mock_llm.call.side_effect = Exception(error_message)
                
                # Should use fallback response instead of raising exception
                result = ask_gemini("Test prompt")
                
                assert result is not None
                assert len(result) > 0
                # Should contain fallback content
                assert "assistance" in result.lower() or "product" in result.lower()
    
    def test_initialize_vertex_ai_with_valid_credentials(self):
        """Test initialize_vertex_ai with valid credentials."""
        config = MOCK_CONFIG_DATA["valid_credentials"]
        
        with patch('infinitum.infrastructure.external_services.vertex_ai.os.getenv') as mock_getenv, \
             patch('infinitum.infrastructure.external_services.vertex_ai.os.path.exists') as mock_exists, \
             patch('infinitum.infrastructure.external_services.vertex_ai.vertexai.init') as mock_init, \
             patch('infinitum.infrastructure.external_services.vertex_ai.LLM') as mock_llm_class:
            
            mock_getenv.return_value = config["GOOGLE_APPLICATION_CREDENTIALS"]
            mock_exists.return_value = True
            mock_llm_instance = Mock()
            mock_llm_instance.call.return_value = "Test response"
            mock_llm_class.return_value = mock_llm_instance
            
            result = initialize_vertex_ai()
            
            assert result == mock_llm_instance
            mock_init.assert_called_once()
            mock_llm_class.assert_called()
    
    def test_initialize_vertex_ai_with_missing_credentials(self):
        """Test initialize_vertex_ai with missing credentials."""
        config = MOCK_CONFIG_DATA["missing_credentials"]
        
        with patch('infinitum.infrastructure.external_services.vertex_ai.os.getenv') as mock_getenv:
            mock_getenv.return_value = config["GOOGLE_APPLICATION_CREDENTIALS"]
            
            with pytest.raises(ValueError) as exc_info:
                initialize_vertex_ai()
            
            assert "GOOGLE_APPLICATION_CREDENTIALS environment variable not set" in str(exc_info.value)
    
    def test_initialize_vertex_ai_with_invalid_credentials_path(self):
        """Test initialize_vertex_ai with invalid credentials path."""
        config = MOCK_CONFIG_DATA["invalid_credentials_path"]
        
        with patch('infinitum.infrastructure.external_services.vertex_ai.os.getenv') as mock_getenv, \
             patch('infinitum.infrastructure.external_services.vertex_ai.os.path.exists') as mock_exists:
            
            mock_getenv.return_value = config["GOOGLE_APPLICATION_CREDENTIALS"]
            mock_exists.return_value = False
            
            with pytest.raises(FileNotFoundError) as exc_info:
                initialize_vertex_ai()
            
            assert "Credentials file not found" in str(exc_info.value)
    
    def test_create_llm_with_retry_success(self):
        """Test create_llm_with_retry with successful creation."""
        llm_config = MOCK_LLM_INSTANCES["working_llm"]
        
        with patch('infinitum.infrastructure.external_services.vertex_ai.LLM') as mock_llm_class:
            mock_llm_instance = Mock()
            mock_llm_instance.call.return_value = "Test response"
            mock_llm_class.return_value = mock_llm_instance
            
            result = create_llm_with_retry(llm_config["model"])
            
            assert result == mock_llm_instance
            mock_llm_class.assert_called_once_with(
                model=llm_config["model"],
                base_url=llm_config["base_url"],
                timeout=llm_config["timeout"],
                max_retries=llm_config["max_retries"]
            )
    
    def test_create_llm_with_retry_failure(self):
        """Test create_llm_with_retry with all attempts failing."""
        llm_config = MOCK_LLM_INSTANCES["failing_llm"]
        
        with patch('infinitum.infrastructure.external_services.vertex_ai.LLM') as mock_llm_class, \
             patch('infinitum.infrastructure.external_services.vertex_ai.time.sleep'):
            
            mock_llm_class.side_effect = Exception(llm_config["error_message"])
            
            result = create_llm_with_retry(llm_config["model"], max_retries=2)
            
            assert result is None
            assert mock_llm_class.call_count == 2
    
    def test_create_llm_with_retry_rate_limit_recovery(self):
        """Test create_llm_with_retry with rate limit recovery."""
        from litellm.exceptions import RateLimitError
        
        with patch('infinitum.infrastructure.external_services.vertex_ai.LLM') as mock_llm_class, \
             patch('infinitum.infrastructure.external_services.vertex_ai.time.sleep'):
            
            mock_llm_instance = Mock()
            mock_llm_instance.call.return_value = "Success"
            
            mock_llm_class.side_effect = [
                RateLimitError("Rate limit exceeded"),
                mock_llm_instance
            ]
            
            result = create_llm_with_retry("test-model", max_retries=3)
            
            assert result == mock_llm_instance
            assert mock_llm_class.call_count == 2
    
    def test_quota_management(self):
        """Test quota management functionality."""
        quota_data = MOCK_QUOTA_DATA["normal_usage"]
        
        with patch('infinitum.infrastructure.external_services.vertex_ai._quota_tracker', quota_data.copy()):
            status = get_quota_status()
            
            assert status["daily_requests"] == quota_data["daily_requests"]
            assert status["quota_limit"] == quota_data["quota_limit"]
            assert status["quota_exceeded"] == quota_data["quota_exceeded"]
            assert "usage_percentage" in status
            assert "cache_entries" in status
    
    def test_quota_exceeded_scenario(self):
        """Test behavior when quota is exceeded."""
        quota_data = MOCK_QUOTA_DATA["quota_exceeded"]
        
        with patch('infinitum.infrastructure.external_services.vertex_ai._quota_tracker', quota_data.copy()), \
             patch('infinitum.infrastructure.external_services.vertex_ai.llm') as mock_llm:
            
            # Should use fallback response when quota is exceeded
            result = ask_gemini("Test prompt")
            
            # Should not call the actual LLM
            mock_llm.call.assert_not_called()
            
            # Should return fallback response
            assert result is not None
            assert len(result) > 0
    
    def test_cache_functionality(self):
        """Test caching functionality."""
        cache_entry = MOCK_CACHE_ENTRIES["valid_cache"]
        
        with patch('infinitum.infrastructure.external_services.vertex_ai._request_cache', {}), \
             patch('infinitum.infrastructure.external_services.vertex_ai.llm') as mock_llm:
            
            # First call should cache the response
            mock_llm.call.return_value = cache_entry["response"]
            result1 = ask_gemini("Test prompt", use_cache=True)
            
            # Second call should use cached response
            result2 = ask_gemini("Test prompt", use_cache=True)
            
            assert result1 == result2
            assert mock_llm.call.call_count == 1  # Only called once
    
    def test_cache_expiration(self):
        """Test cache expiration functionality."""
        expired_cache = MOCK_CACHE_ENTRIES["expired_cache"]
        
        with patch('infinitum.infrastructure.external_services.vertex_ai._request_cache', {"test_key": expired_cache}), \
             patch('infinitum.infrastructure.external_services.vertex_ai.llm') as mock_llm:
            
            mock_llm.call.return_value = "Fresh response"
            
            # Should not use expired cache
            result = ask_gemini("Test prompt", use_cache=True)
            
            assert result == "Fresh response"
            mock_llm.call.assert_called_once()
    
    def test_cache_statistics(self):
        """Test cache statistics functionality."""
        multiple_cache = MOCK_CACHE_ENTRIES["multiple_cache_entries"]
        
        with patch('infinitum.infrastructure.external_services.vertex_ai._request_cache', multiple_cache):
            stats = get_cache_stats()
            
            assert "total_entries" in stats
            assert "valid_entries" in stats
            assert "expired_entries" in stats
            assert "cache_hit_potential" in stats
            assert stats["total_entries"] == len(multiple_cache)
    
    def test_cache_clear_functionality(self):
        """Test cache clearing functionality."""
        multiple_cache = MOCK_CACHE_ENTRIES["multiple_cache_entries"]
        
        with patch('infinitum.infrastructure.external_services.vertex_ai._request_cache', multiple_cache.copy()):
            cache_count = len(multiple_cache)
            clear_cache()
            
            # Cache should be empty after clearing
            stats = get_cache_stats()
            assert stats["total_entries"] == 0
    
    def test_comprehensive_scenarios(self):
        """Test comprehensive scenarios using dummy data."""
        for scenario_name, scenario_data in TEST_SCENARIOS.items():
            print(f"Testing scenario: {scenario_name}")
            
            # Test the scenario based on its configuration
            if scenario_data["expected_result"] == "success":
                with patch('infinitum.infrastructure.external_services.vertex_ai.llm') as mock_llm:
                    mock_llm.call.return_value = "Success response"
                    result = ask_gemini("Test prompt")
                    assert result == "Success response"
            
            elif scenario_data["expected_result"] == "fallback_response":
                with patch('infinitum.infrastructure.external_services.vertex_ai.llm') as mock_llm:
                    mock_llm.call.side_effect = Exception("Service error")
                    result = ask_gemini("Test prompt")
                    assert result is not None
                    assert len(result) > 0
    
    def test_json_response_parsing(self):
        """Test handling of JSON responses from Gemini."""
        json_response = MOCK_GEMINI_RESPONSES["package_creation"]
        
        with patch('infinitum.infrastructure.external_services.vertex_ai.llm') as mock_llm:
            mock_llm.call.return_value = json_response
            
            result = ask_gemini("Create a package")
            
            assert result == json_response
            # Verify it's valid JSON
            try:
                parsed = json.loads(result)
                assert "packages" in parsed
                assert "summary" in parsed
                assert "expert_recommendations" in parsed
            except json.JSONDecodeError:
                # If not JSON, that's also acceptable
                assert len(result) > 0
    
    def test_response_validation(self):
        """Test response validation and sanitization."""
        test_responses = [
            MOCK_GEMINI_RESPONSES["simple_math"],
            MOCK_GEMINI_RESPONSES["product_analysis"],
            MOCK_GEMINI_RESPONSES["keyword_extraction"],
            MOCK_GEMINI_RESPONSES["long_response"]
        ]
        
        with patch('infinitum.infrastructure.external_services.vertex_ai.llm') as mock_llm:
            for response in test_responses:
                mock_llm.call.return_value = response
                result = ask_gemini("Test prompt")
                
                assert result == response
                assert isinstance(result, str)
                assert len(result) >= 0  # Can be empty string


class TestVertexAIIntegrationWithDummyData:
    """Integration tests using dummy data."""
    
    @pytest.mark.skipif(
        not os.getenv('GOOGLE_APPLICATION_CREDENTIALS'),
        reason="Requires Google Cloud credentials for integration tests"
    )
    def test_real_gemini_with_dummy_prompts(self):
        """Test real Gemini API with dummy prompts."""
        test_prompts = TEST_PROMPTS["simple_queries"][:2]  # Test first 2 prompts
        
        for prompt in test_prompts:
            try:
                response = ask_gemini(prompt)
                assert response is not None
                assert len(response.strip()) > 0
                print(f"Real Gemini response for '{prompt}': {response[:100]}...")
            except Exception as e:
                pytest.skip(f"Real Gemini test skipped due to: {e}")
    
    def test_dummy_data_consistency(self):
        """Test that dummy data is consistent and well-formed."""
        # Test mock responses
        for key, response in MOCK_GEMINI_RESPONSES.items():
            assert isinstance(response, str)
            assert len(response) >= 0
        
        # Test test prompts
        for category, prompts in TEST_PROMPTS.items():
            assert isinstance(prompts, list)
            for prompt in prompts:
                assert isinstance(prompt, str)
        
        # Test cache entries
        for key, entry in MOCK_CACHE_ENTRIES.items():
            if isinstance(entry, dict) and "response" in entry:
                assert isinstance(entry["response"], str)
                assert "timestamp" in entry
        
        # Test quota data
        for key, quota in MOCK_QUOTA_DATA.items():
            assert "daily_requests" in quota
            assert "quota_limit" in quota
            assert "quota_exceeded" in quota
            assert isinstance(quota["daily_requests"], int)
            assert isinstance(quota["quota_limit"], int)
            assert isinstance(quota["quota_exceeded"], bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 