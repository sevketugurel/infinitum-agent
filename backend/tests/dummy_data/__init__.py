"""
Dummy data package for testing.

This package contains comprehensive dummy data for testing various services
in the Infinitum AI Agent, including Vertex AI, Vector Search, and other components.
"""

from .vertex_ai_dummy_data import (
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

__all__ = [
    "MOCK_GEMINI_RESPONSES",
    "TEST_PROMPTS", 
    "MOCK_CACHE_ENTRIES",
    "MOCK_QUOTA_DATA",
    "MOCK_LLM_INSTANCES",
    "MOCK_ERROR_RESPONSES",
    "MOCK_CONFIG_DATA",
    "MOCK_API_RESPONSES",
    "TEST_SCENARIOS",
    "get_mock_response_for_prompt",
    "create_mock_cache_entry",
    "get_test_prompts_by_category",
    "get_mock_quota_data",
    "get_test_scenario"
] 