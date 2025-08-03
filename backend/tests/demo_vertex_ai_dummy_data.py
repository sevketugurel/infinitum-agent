#!/usr/bin/env python3
"""
Demonstration script for Vertex AI dummy data.

This script shows how to use the dummy data for testing and development
without requiring actual GCP credentials or API calls.
"""

import sys
import os
import json
from datetime import datetime

# Add the tests directory to the path
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


def demo_mock_responses():
    """Demonstrate mock Gemini responses."""
    print("=" * 60)
    print("MOCK GEMINI RESPONSES DEMO")
    print("=" * 60)
    
    for response_type, response in MOCK_GEMINI_RESPONSES.items():
        print(f"\n📝 {response_type.upper()}:")
        print("-" * 40)
        preview = response[:200] + "..." if len(response) > 200 else response
        print(preview)
        print(f"Length: {len(response)} characters")


def demo_test_prompts():
    """Demonstrate test prompts by category."""
    print("\n" + "=" * 60)
    print("TEST PROMPTS BY CATEGORY")
    print("=" * 60)
    
    for category, prompts in TEST_PROMPTS.items():
        print(f"\n🔍 {category.upper()}:")
        print("-" * 40)
        for i, prompt in enumerate(prompts[:3], 1):  # Show first 3 prompts
            print(f"{i}. {prompt}")
        if len(prompts) > 3:
            print(f"... and {len(prompts) - 3} more prompts")


def demo_cache_functionality():
    """Demonstrate cache functionality."""
    print("\n" + "=" * 60)
    print("CACHE FUNCTIONALITY DEMO")
    print("=" * 60)
    
    # Create a mock cache entry
    prompt = "What are the best wireless headphones?"
    response = "Based on reviews, the Sony WH-1000XM4 is highly recommended."
    
    cache_entry = create_mock_cache_entry(prompt, response, hours_old=2)
    print(f"\n📦 Created cache entry:")
    print(f"Prompt: {cache_entry['prompt_preview']}")
    print(f"Response: {cache_entry['response']}")
    print(f"Timestamp: {cache_entry['timestamp']}")
    
    # Show existing cache entries
    print(f"\n🗄️ Existing cache entries:")
    for key, entry in MOCK_CACHE_ENTRIES.items():
        if isinstance(entry, dict) and "response" in entry:
            print(f"- {key}: {entry['prompt_preview']}")


def demo_quota_management():
    """Demonstrate quota management scenarios."""
    print("\n" + "=" * 60)
    print("QUOTA MANAGEMENT DEMO")
    print("=" * 60)
    
    for scenario, quota_data in MOCK_QUOTA_DATA.items():
        usage_percentage = (quota_data["daily_requests"] / quota_data["quota_limit"]) * 100
        print(f"\n📊 {scenario.upper()}:")
        print(f"   Daily requests: {quota_data['daily_requests']}/{quota_data['quota_limit']}")
        print(f"   Usage: {usage_percentage:.1f}%")
        print(f"   Quota exceeded: {quota_data['quota_exceeded']}")


def demo_error_scenarios():
    """Demonstrate error scenarios."""
    print("\n" + "=" * 60)
    print("ERROR SCENARIOS DEMO")
    print("=" * 60)
    
    for error_type, error_data in MOCK_ERROR_RESPONSES.items():
        print(f"\n❌ {error_type.upper()}:")
        print(f"   Type: {error_data['type']}")
        print(f"   Message: {error_data['message']}")
        if error_data['retry_after']:
            print(f"   Retry after: {error_data['retry_after']} seconds")


def demo_test_scenarios():
    """Demonstrate test scenarios."""
    print("\n" + "=" * 60)
    print("TEST SCENARIOS DEMO")
    print("=" * 60)
    
    for scenario_name, scenario_data in TEST_SCENARIOS.items():
        print(f"\n🧪 {scenario_name.upper()}:")
        print(f"   Description: {scenario_data['description']}")
        print(f"   Credentials: {scenario_data['credentials']}")
        print(f"   Quota status: {scenario_data['quota_status']}")
        print(f"   Expected result: {scenario_data['expected_result']}")


def demo_smart_response_matching():
    """Demonstrate smart response matching."""
    print("\n" + "=" * 60)
    print("SMART RESPONSE MATCHING DEMO")
    print("=" * 60)
    
    test_prompts = [
        "What is 2+2?",
        "Extract keywords from this product description about headphones",
        "Create a package for professional content creation",
        "Analyze this product and provide recommendations",
        "Find the best wireless headphones under $200",
        "This is a very long prompt that should trigger the long response handler",
        "",  # Empty prompt
    ]
    
    for prompt in test_prompts:
        response = get_mock_response_for_prompt(prompt)
        print(f"\n🤖 Prompt: {prompt[:50]}{'...' if len(prompt) > 50 else ''}")
        print(f"   Response type: {type(response).__name__}")
        print(f"   Response preview: {response[:100]}{'...' if len(response) > 100 else ''}")


def demo_configuration_scenarios():
    """Demonstrate configuration scenarios."""
    print("\n" + "=" * 60)
    print("CONFIGURATION SCENARIOS DEMO")
    print("=" * 60)
    
    for config_name, config_data in MOCK_CONFIG_DATA.items():
        print(f"\n⚙️ {config_name.upper()}:")
        for key, value in config_data.items():
            if key == "GOOGLE_APPLICATION_CREDENTIALS" and value:
                # Mask sensitive data
                masked_value = "***" + str(value)[-20:] if len(str(value)) > 20 else "***"
                print(f"   {key}: {masked_value}")
            else:
                print(f"   {key}: {value}")


def demo_api_response_structures():
    """Demonstrate API response structures."""
    print("\n" + "=" * 60)
    print("API RESPONSE STRUCTURES DEMO")
    print("=" * 60)
    
    for response_type, response_data in MOCK_API_RESPONSES.items():
        print(f"\n📡 {response_type.upper()}:")
        print(f"   Status: {response_data['status']}")
        if 'data' in response_data:
            print(f"   Model used: {response_data['data'].get('model_used', 'N/A')}")
            print(f"   Tokens used: {response_data['data'].get('tokens_used', 'N/A')}")
            print(f"   Response time: {response_data['data'].get('response_time', 'N/A')}s")
        if 'error' in response_data:
            print(f"   Error code: {response_data['error']['code']}")
            print(f"   Error message: {response_data['error']['message']}")


def main():
    """Run all demonstrations."""
    print("🚀 VERTEX AI DUMMY DATA DEMONSTRATION")
    print("=" * 60)
    print(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("This demo shows how to use dummy data for Vertex AI testing")
    print("without requiring actual GCP credentials or API calls.")
    
    try:
        demo_mock_responses()
        demo_test_prompts()
        demo_cache_functionality()
        demo_quota_management()
        demo_error_scenarios()
        demo_test_scenarios()
        demo_smart_response_matching()
        demo_configuration_scenarios()
        demo_api_response_structures()
        
        print("\n" + "=" * 60)
        print("✅ DEMONSTRATION COMPLETE")
        print("=" * 60)
        print("\nYou can now use this dummy data for:")
        print("• Unit testing without API calls")
        print("• Development without credentials")
        print("• CI/CD pipeline testing")
        print("• Performance testing")
        print("• Error scenario testing")
        
    except Exception as e:
        print(f"\n❌ Error during demonstration: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main()) 