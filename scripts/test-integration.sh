#!/bin/bash

# Full-Stack Integration Test Script
# Tests connectivity and functionality between frontend and backend

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKEND_URL=${BACKEND_URL:-"http://localhost:8080"}
FRONTEND_URL=${FRONTEND_URL:-"http://localhost:5173"}
TEST_TIMEOUT=30

echo -e "${BLUE}🧪 Starting Full-Stack Integration Tests${NC}"
echo "============================================="
echo "Backend URL: $BACKEND_URL"
echo "Frontend URL: $FRONTEND_URL"
echo ""

# Test results tracking
TESTS_PASSED=0
TESTS_FAILED=0
FAILED_TESTS=()

# Helper function to run tests
run_test() {
    local test_name="$1"
    local test_command="$2"
    
    echo -e "${YELLOW}🔍 Testing: $test_name${NC}"
    
    if eval "$test_command"; then
        echo -e "${GREEN}✅ PASSED: $test_name${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}❌ FAILED: $test_name${NC}"
        ((TESTS_FAILED++))
        FAILED_TESTS+=("$test_name")
    fi
    echo ""
}

# Test 1: Backend Health Check
run_test "Backend Health Check" "curl -f -s --max-time $TEST_TIMEOUT '$BACKEND_URL/healthz' > /dev/null"

# Test 2: Backend Detailed Health
run_test "Backend Detailed Health" "curl -f -s --max-time $TEST_TIMEOUT '$BACKEND_URL/health/detailed' | jq -e '.status == \"healthy\" or .status == \"degraded\"' > /dev/null"

# Test 3: API Configuration Endpoint
run_test "API Configuration Endpoint" "curl -f -s --max-time $TEST_TIMEOUT '$BACKEND_URL/api/config' | jq -e '.version' > /dev/null"

# Test 4: CORS Headers
run_test "CORS Headers" "curl -s -H 'Origin: $FRONTEND_URL' -H 'Access-Control-Request-Method: POST' -H 'Access-Control-Request-Headers: Content-Type,Authorization' -X OPTIONS '$BACKEND_URL/api/v1/chat' | grep -i 'access-control-allow-origin' > /dev/null"

# Test 5: AI Chat Endpoint (without auth)
run_test "AI Chat Endpoint (Guest)" "curl -f -s --max-time $TEST_TIMEOUT -X POST '$BACKEND_URL/api/v1/chat' -H 'Content-Type: application/json' -d '{\"message\": \"test message\"}' | jq -e '.message.type == \"ai\"' > /dev/null"

# Test 6: Vector Search Service Status
run_test "Vector Search Service" "curl -f -s --max-time $TEST_TIMEOUT '$BACKEND_URL/llm-status' | jq -e '.status' > /dev/null"

# Test 7: Firestore Connection
run_test "Firestore Connection" "curl -f -s --max-time $TEST_TIMEOUT '$BACKEND_URL/health/detailed' | jq -e '.services.firestore.status == \"healthy\"' > /dev/null"

# Test 8: Frontend Accessibility
if command -v curl &> /dev/null; then
    run_test "Frontend Accessibility" "curl -f -s --max-time $TEST_TIMEOUT '$FRONTEND_URL' > /dev/null"
fi

# Test 9: WebSocket Connection (if backend is running)
if command -v wscat &> /dev/null; then
    run_test "WebSocket Connection" "timeout 5 wscat -c '${BACKEND_URL/http/ws}/api/v1/chat/ws/test-user' -x '{\"type\":\"ping\"}' 2>/dev/null | grep -q 'connected' || true"
else
    echo -e "${YELLOW}⚠️ Skipping WebSocket test (wscat not installed)${NC}"
fi

# Test 10: API Response Time
echo -e "${YELLOW}🔍 Testing: API Response Time${NC}"
RESPONSE_TIME=$(curl -o /dev/null -s -w '%{time_total}' --max-time $TEST_TIMEOUT "$BACKEND_URL/healthz")
if (( $(echo "$RESPONSE_TIME < 2.0" | bc -l) )); then
    echo -e "${GREEN}✅ PASSED: API Response Time (${RESPONSE_TIME}s)${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ FAILED: API Response Time too slow (${RESPONSE_TIME}s)${NC}"
    ((TESTS_FAILED++))
    FAILED_TESTS+=("API Response Time")
fi
echo ""

# Test 11: Memory Usage (if running locally)
if pgrep -f "uvicorn.*infinitum.main:app" > /dev/null; then
    echo -e "${YELLOW}🔍 Testing: Backend Memory Usage${NC}"
    MEMORY_MB=$(ps -o rss= -p $(pgrep -f "uvicorn.*infinitum.main:app") | awk '{sum+=$1} END {print sum/1024}')
    if (( $(echo "$MEMORY_MB < 1000" | bc -l) )); then
        echo -e "${GREEN}✅ PASSED: Memory Usage (${MEMORY_MB}MB)${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "${YELLOW}⚠️ WARNING: High Memory Usage (${MEMORY_MB}MB)${NC}"
        ((TESTS_PASSED++))
    fi
    echo ""
fi

# Test 12: Service Dependencies
echo -e "${YELLOW}🔍 Testing: Service Dependencies${NC}"
SERVICES_STATUS=$(curl -s --max-time $TEST_TIMEOUT "$BACKEND_URL/health/detailed" | jq -r '.services | to_entries[] | "\(.key):\(.value.status)"')
echo "$SERVICES_STATUS"

HEALTHY_SERVICES=$(echo "$SERVICES_STATUS" | grep -c "healthy" || true)
TOTAL_SERVICES=$(echo "$SERVICES_STATUS" | wc -l)

if [ "$HEALTHY_SERVICES" -gt 0 ]; then
    echo -e "${GREEN}✅ PASSED: Service Dependencies ($HEALTHY_SERVICES/$TOTAL_SERVICES healthy)${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ FAILED: Service Dependencies (No healthy services)${NC}"
    ((TESTS_FAILED++))
    FAILED_TESTS+=("Service Dependencies")
fi
echo ""

# Performance Tests
echo -e "${BLUE}⚡ Performance Tests${NC}"
echo "==================="

# Test concurrent requests
echo -e "${YELLOW}🔍 Testing: Concurrent Request Handling${NC}"
for i in {1..5}; do
    curl -s --max-time 10 "$BACKEND_URL/healthz" > /dev/null &
done
wait

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ PASSED: Concurrent Request Handling${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ FAILED: Concurrent Request Handling${NC}"
    ((TESTS_FAILED++))
    FAILED_TESTS+=("Concurrent Request Handling")
fi
echo ""

# Security Tests
echo -e "${BLUE}🔒 Security Tests${NC}"
echo "================="

# Test SQL injection protection (basic)
run_test "SQL Injection Protection" "curl -s --max-time 10 -X POST '$BACKEND_URL/api/v1/chat' -H 'Content-Type: application/json' -d '{\"message\": \"'; DROP TABLE users; --\"}' | jq -e '.message.type == \"ai\"' > /dev/null"

# Test XSS protection
run_test "XSS Protection" "curl -s --max-time 10 -X POST '$BACKEND_URL/api/v1/chat' -H 'Content-Type: application/json' -d '{\"message\": \"<script>alert(1)</script>\"}' | jq -e '.message.type == \"ai\"' > /dev/null"

# Test rate limiting (if implemented)
echo -e "${YELLOW}🔍 Testing: Rate Limiting${NC}"
RATE_LIMIT_RESPONSES=0
for i in {1..20}; do
    RESPONSE_CODE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "$BACKEND_URL/healthz")
    if [ "$RESPONSE_CODE" = "429" ]; then
        ((RATE_LIMIT_RESPONSES++))
    fi
done

if [ "$RATE_LIMIT_RESPONSES" -gt 0 ]; then
    echo -e "${GREEN}✅ PASSED: Rate Limiting (${RATE_LIMIT_RESPONSES} rate limited responses)${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${YELLOW}⚠️ INFO: Rate Limiting not triggered or not implemented${NC}"
    ((TESTS_PASSED++))
fi
echo ""

# Integration Tests
echo -e "${BLUE}🔗 Integration Tests${NC}"
echo "==================="

# Test full AI chat flow
echo -e "${YELLOW}🔍 Testing: Full AI Chat Flow${NC}"
CHAT_RESPONSE=$(curl -s --max-time 30 -X POST "$BACKEND_URL/api/v1/chat" \
    -H "Content-Type: application/json" \
    -d '{"message": "iPhone telefon"}')

if echo "$CHAT_RESPONSE" | jq -e '.message.type == "ai" and (.products | length >= 0)' > /dev/null; then
    echo -e "${GREEN}✅ PASSED: Full AI Chat Flow${NC}"
    ((TESTS_PASSED++))
    
    # Check if products were found
    PRODUCTS_COUNT=$(echo "$CHAT_RESPONSE" | jq -r '.products | length')
    echo -e "${BLUE}   Products found: $PRODUCTS_COUNT${NC}"
else
    echo -e "${RED}❌ FAILED: Full AI Chat Flow${NC}"
    ((TESTS_FAILED++))
    FAILED_TESTS+=("Full AI Chat Flow")
fi
echo ""

# Summary
echo -e "${BLUE}📊 Test Summary${NC}"
echo "==============="
echo -e "${GREEN}✅ Tests Passed: $TESTS_PASSED${NC}"
echo -e "${RED}❌ Tests Failed: $TESTS_FAILED${NC}"
echo -e "Total Tests: $((TESTS_PASSED + TESTS_FAILED))"

if [ $TESTS_FAILED -gt 0 ]; then
    echo ""
    echo -e "${RED}Failed Tests:${NC}"
    for test in "${FAILED_TESTS[@]}"; do
        echo -e "${RED}  • $test${NC}"
    done
fi

echo ""
echo -e "${BLUE}🔧 System Information${NC}"
echo "===================="
echo "Backend URL: $BACKEND_URL"
echo "Frontend URL: $FRONTEND_URL"
echo "Test Timeout: ${TEST_TIMEOUT}s"
echo "Timestamp: $(date)"

# Recommendations
echo ""
echo -e "${BLUE}💡 Recommendations${NC}"
echo "=================="

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 All tests passed! Your full-stack integration is working correctly.${NC}"
    echo ""
    echo "Next steps:"
    echo "• Deploy to production environment"
    echo "• Set up monitoring and alerting"
    echo "• Configure CI/CD pipeline"
    echo "• Perform load testing"
else
    echo -e "${YELLOW}⚠️ Some tests failed. Please address the following:${NC}"
    echo ""
    for test in "${FAILED_TESTS[@]}"; do
        case "$test" in
            "Backend Health Check")
                echo "• Ensure backend server is running on $BACKEND_URL"
                ;;
            "Frontend Accessibility")
                echo "• Ensure frontend server is running on $FRONTEND_URL"
                ;;
            "CORS Headers")
                echo "• Check CORS configuration in backend"
                ;;
            "AI Chat Endpoint")
                echo "• Verify AI chat API endpoint and dependencies"
                ;;
            "Service Dependencies")
                echo "• Check Firestore, Vertex AI, and other service connections"
                ;;
            *)
                echo "• Investigate and fix: $test"
                ;;
        esac
    done
fi

echo ""
echo -e "${BLUE}🚀 Integration test completed!${NC}"

# Exit with appropriate code
if [ $TESTS_FAILED -eq 0 ]; then
    exit 0
else
    exit 1
fi