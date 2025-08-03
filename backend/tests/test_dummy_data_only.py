"""
Test file for dummy data functionality only.

This file tests the dummy data without requiring actual Vertex AI module imports,
making it suitable for testing the dummy data structure and utility functions.
"""

import pytest
import json
from datetime import datetime, timedelta
import sys
import os

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


class TestDummyDataStructure:
    """Test the structure and content of dummy data."""
    
    def test_mock_gemini_responses_structure(self):
        """Test that mock Gemini responses are properly structured."""
        assert isinstance(MOCK_GEMINI_RESPONSES, dict)
        assert len(MOCK_GEMINI_RESPONSES) > 0
        
        for key, response in MOCK_GEMINI_RESPONSES.items():
            assert isinstance(response, str)
            assert len(response) >= 0  # Can be empty string
    
    def test_test_prompts_structure(self):
        """Test that test prompts are properly structured."""
        assert isinstance(TEST_PROMPTS, dict)
        assert len(TEST_PROMPTS) > 0
        
        for category, prompts in TEST_PROMPTS.items():
            assert isinstance(prompts, list)
            assert len(prompts) > 0
            for prompt in prompts:
                assert isinstance(prompt, str)
    
    def test_cache_entries_structure(self):
        """Test that cache entries are properly structured."""
        assert isinstance(MOCK_CACHE_ENTRIES, dict)
        assert len(MOCK_CACHE_ENTRIES) > 0
        
        for key, entry in MOCK_CACHE_ENTRIES.items():
            if isinstance(entry, dict) and "response" in entry:
                assert isinstance(entry["response"], str)
                assert "timestamp" in entry
                assert "prompt_preview" in entry
    
    def test_quota_data_structure(self):
        """Test that quota data is properly structured."""
        assert isinstance(MOCK_QUOTA_DATA, dict)
        assert len(MOCK_QUOTA_DATA) > 0
        
        for key, quota in MOCK_QUOTA_DATA.items():
            assert "daily_requests" in quota
            assert "quota_limit" in quota
            assert "quota_exceeded" in quota
            assert isinstance(quota["daily_requests"], int)
            assert isinstance(quota["quota_limit"], int)
            assert isinstance(quota["quota_exceeded"], bool)
    
    def test_error_responses_structure(self):
        """Test that error responses are properly structured."""
        assert isinstance(MOCK_ERROR_RESPONSES, dict)
        assert len(MOCK_ERROR_RESPONSES) > 0
        
        for key, error in MOCK_ERROR_RESPONSES.items():
            assert "type" in error
            assert "message" in error
            assert isinstance(error["type"], str)
            assert isinstance(error["message"], str)
    
    def test_config_data_structure(self):
        """Test that configuration data is properly structured."""
        assert isinstance(MOCK_CONFIG_DATA, dict)
        assert len(MOCK_CONFIG_DATA) > 0
        
        for key, config in MOCK_CONFIG_DATA.items():
            assert "GCP_PROJECT_ID" in config
            assert "GEMINI_MODEL" in config
            assert "GEMINI_DAILY_QUOTA" in config


class TestUtilityFunctions:
    """Test the utility functions for dummy data."""
    
    def test_get_mock_response_for_prompt(self):
        """Test the smart response matching function."""
        # Test keyword extraction
        response = get_mock_response_for_prompt("Extract keywords from this product")
        assert response == MOCK_GEMINI_RESPONSES["keyword_extraction"]
        
        # Test package creation
        response = get_mock_response_for_prompt("Create a package for professional equipment")
        assert response == MOCK_GEMINI_RESPONSES["package_creation"]
        
        # Test product analysis
        response = get_mock_response_for_prompt("Analyze this product")
        assert response == MOCK_GEMINI_RESPONSES["technical_analysis"]
        
        # Test simple math
        response = get_mock_response_for_prompt("What is 2+2?")
        assert response == MOCK_GEMINI_RESPONSES["simple_math"]
        
        # Test long prompt
        long_prompt = "A" * 1000
        response = get_mock_response_for_prompt(long_prompt)
        assert response == MOCK_GEMINI_RESPONSES["long_response"]
        
        # Test empty prompt
        response = get_mock_response_for_prompt("")
        assert response == MOCK_GEMINI_RESPONSES["empty_response"]
    
    def test_create_mock_cache_entry(self):
        """Test cache entry creation."""
        prompt = "Test prompt"
        response = "Test response"
        hours_old = 2
        
        cache_entry = create_mock_cache_entry(prompt, response, hours_old)
        
        assert cache_entry["response"] == response
        assert cache_entry["prompt_preview"] == prompt
        assert "timestamp" in cache_entry
        
        # Verify timestamp is in the past
        timestamp = datetime.fromisoformat(cache_entry["timestamp"])
        assert datetime.now() - timestamp > timedelta(hours=1)
    
    def test_get_test_prompts_by_category(self):
        """Test getting prompts by category."""
        product_prompts = get_test_prompts_by_category("product_related")
        assert isinstance(product_prompts, list)
        assert len(product_prompts) > 0
        
        technical_prompts = get_test_prompts_by_category("technical_queries")
        assert isinstance(technical_prompts, list)
        assert len(technical_prompts) > 0
        
        # Test non-existent category
        empty_prompts = get_test_prompts_by_category("non_existent")
        assert isinstance(empty_prompts, list)
        assert len(empty_prompts) == 0
    
    def test_get_mock_quota_data(self):
        """Test getting quota data by scenario."""
        quota_data = get_mock_quota_data("normal_usage")
        assert quota_data["daily_requests"] == 50
        assert quota_data["quota_limit"] == 200
        assert quota_data["quota_exceeded"] is False
        
        quota_data = get_mock_quota_data("quota_exceeded")
        assert quota_data["daily_requests"] == 200
        assert quota_data["quota_limit"] == 200
        assert quota_data["quota_exceeded"] is True
        
        # Test default fallback
        quota_data = get_mock_quota_data("non_existent")
        assert quota_data["daily_requests"] == 50  # Default to normal_usage
    
    def test_get_test_scenario(self):
        """Test getting test scenarios."""
        scenario = get_test_scenario("normal_operation")
        assert scenario["description"] == "Normal operation with valid credentials and quota"
        assert scenario["expected_result"] == "success"
        
        scenario = get_test_scenario("quota_exceeded")
        assert scenario["description"] == "Operation when daily quota is exceeded"
        assert scenario["expected_result"] == "fallback_response"
        
        # Test non-existent scenario
        empty_scenario = get_test_scenario("non_existent")
        assert isinstance(empty_scenario, dict)
        assert len(empty_scenario) == 0


class TestDummyDataContent:
    """Test the content and validity of dummy data."""
    
    def test_json_responses_are_valid(self):
        """Test that JSON responses are valid JSON."""
        json_response = MOCK_GEMINI_RESPONSES["keyword_extraction"]
        try:
            parsed = json.loads(json_response)
            assert isinstance(parsed, list)
        except json.JSONDecodeError:
            pytest.fail("Keyword extraction response should be valid JSON")
        
        package_response = MOCK_GEMINI_RESPONSES["package_creation"]
        try:
            parsed = json.loads(package_response)
            assert "packages" in parsed
            assert "summary" in parsed
            assert "expert_recommendations" in parsed
        except json.JSONDecodeError:
            pytest.fail("Package creation response should be valid JSON")
    
    def test_prompts_are_diverse(self):
        """Test that prompts cover different scenarios."""
        all_prompts = []
        for category, prompts in TEST_PROMPTS.items():
            all_prompts.extend(prompts)
        
        # Check for diversity in prompt types
        assert any("extract" in prompt.lower() for prompt in all_prompts)
        assert any("analyze" in prompt.lower() for prompt in all_prompts)
        assert any("create" in prompt.lower() for prompt in all_prompts)
        assert any("find" in prompt.lower() for prompt in all_prompts)
    
    def test_error_scenarios_are_comprehensive(self):
        """Test that error scenarios cover common error types."""
        error_types = [error["type"] for error in MOCK_ERROR_RESPONSES.values()]
        
        assert "RateLimitError" in error_types
        assert "ConnectionError" in error_types
        assert "AuthenticationError" in error_types
        assert "ServiceUnavailableError" in error_types
        assert "InternalServerError" in error_types
    
    def test_quota_scenarios_are_realistic(self):
        """Test that quota scenarios are realistic."""
        for scenario, quota in MOCK_QUOTA_DATA.items():
            assert 0 <= quota["daily_requests"] <= quota["quota_limit"]
            assert quota["quota_limit"] > 0
            
            if quota["quota_exceeded"]:
                assert quota["daily_requests"] >= quota["quota_limit"]
    
    def test_cache_entries_have_valid_timestamps(self):
        """Test that cache entries have valid timestamps."""
        for key, entry in MOCK_CACHE_ENTRIES.items():
            if isinstance(entry, dict) and "timestamp" in entry:
                try:
                    timestamp = datetime.fromisoformat(entry["timestamp"])
                    assert isinstance(timestamp, datetime)
                except ValueError:
                    pytest.fail(f"Invalid timestamp in cache entry {key}")


class TestDummyDataIntegration:
    """Test integration aspects of dummy data."""
    
    def test_all_categories_have_prompts(self):
        """Test that all prompt categories have content."""
        for category, prompts in TEST_PROMPTS.items():
            assert len(prompts) > 0, f"Category {category} has no prompts"
    
    def test_all_scenarios_have_required_fields(self):
        """Test that all test scenarios have required fields."""
        required_fields = ["description", "credentials", "quota_status", "expected_result"]
        
        for scenario_name, scenario in TEST_SCENARIOS.items():
            for field in required_fields:
                assert field in scenario, f"Scenario {scenario_name} missing field {field}"
    
    def test_config_data_consistency(self):
        """Test that configuration data is consistent."""
        for config_name, config in MOCK_CONFIG_DATA.items():
            # All configs should have the same basic structure
            assert "GCP_PROJECT_ID" in config
            assert "GEMINI_MODEL" in config
            assert "GEMINI_DAILY_QUOTA" in config
            
            # Project ID should be consistent
            assert config["GCP_PROJECT_ID"] in ["test-project-123", "infinitum-agent"]
            
            # Model should be a valid Gemini model
            assert "gemini" in config["GEMINI_MODEL"].lower()
            
            # Quota should be reasonable
            assert 0 < config["GEMINI_DAILY_QUOTA"] <= 1000


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 