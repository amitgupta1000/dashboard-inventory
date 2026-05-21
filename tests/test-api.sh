#!/bin/bash

# API Testing Script for Crystal Supplier Email Service
# Use this script to test API endpoints manually

BASE_URL="${1:-http://localhost:8000}"
echo "Testing API at: $BASE_URL"
echo "=============================================="

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test 1: Health Check
echo -e "\n${BLUE}1. Testing Health Check${NC}"
curl -X GET "$BASE_URL/health" -H "Content-Type: application/json"
echo ""

# Test 2: Get Suppliers
echo -e "\n${BLUE}2. Testing Get Suppliers${NC}"
curl -X GET "$BASE_URL/api/suppliers" -H "Content-Type: application/json"
echo ""

# Test 3: Get All Jobs
echo -e "\n${BLUE}3. Testing Get All Jobs${NC}"
curl -X GET "$BASE_URL/api/jobs" -H "Content-Type: application/json"
echo ""

# Test 4: Create Job
echo -e "\n${BLUE}4. Testing Create Job${NC}"
JOB_RESPONSE=$(curl -s -X POST "$BASE_URL/api/jobs/start" \
  -H "Content-Type: application/json" \
  -d '{
    "chemical_query": "Test: 20000 MT Methanol CFR Singapore",
    "supplier_emails": ["test1@example.com", "test2@example.com"]
  }')
echo "$JOB_RESPONSE"

# Extract job_id from response
JOB_ID=$(echo "$JOB_RESPONSE" | grep -o '"job_id": [0-9]*' | head -1 | grep -o '[0-9]*')

if [ -n "$JOB_ID" ]; then
    echo -e "\n${GREEN}Created job with ID: $JOB_ID${NC}"
    
    # Test 5: Get Job Details
    echo -e "\n${BLUE}5. Testing Get Job Details (Job ID: $JOB_ID)${NC}"
    curl -X GET "$BASE_URL/api/jobs/$JOB_ID" \
      -H "Content-Type: application/json"
    echo ""
    
    # Test 6: Get Job Suppliers
    echo -e "\n${BLUE}6. Testing Get Job Suppliers (Job ID: $JOB_ID)${NC}"
    curl -X GET "$BASE_URL/api/jobs/$JOB_ID/suppliers" \
      -H "Content-Type: application/json"
    echo ""
    
    # Test 7: Get Job Insights
    echo -e "\n${BLUE}7. Testing Get Job Insights (Job ID: $JOB_ID)${NC}"
    curl -X GET "$BASE_URL/api/jobs/$JOB_ID/insights" \
      -H "Content-Type: application/json"
    echo ""
    
    # Test 8: Refresh Insights
    echo -e "\n${BLUE}8. Testing Refresh Insights (Job ID: $JOB_ID)${NC}"
    curl -X POST "$BASE_URL/api/jobs/$JOB_ID/insights/refresh" \
      -H "Content-Type: application/json"
    echo ""
    
    # Test 9: Get Job Statistics
    echo -e "\n${BLUE}9. Testing Get Job Statistics (Job ID: $JOB_ID)${NC}"
    curl -X GET "$BASE_URL/api/stats/job/$JOB_ID" \
      -H "Content-Type: application/json"
    echo ""
    
    # Test 10: Close Job
    echo -e "\n${BLUE}10. Testing Close Job (Job ID: $JOB_ID)${NC}"
    curl -X POST "$BASE_URL/api/jobs/$JOB_ID/close" \
      -H "Content-Type: application/json"
    echo ""
fi

# Test 11: Get Summary Statistics
echo -e "\n${BLUE}11. Testing Get Summary Statistics${NC}"
curl -X GET "$BASE_URL/api/stats/summary" \
  -H "Content-Type: application/json"
echo ""

# Test 12: Get Insights by Supplier
echo -e "\n${BLUE}12. Testing Get Insights by Supplier${NC}"
curl -X GET "$BASE_URL/api/insights/by-supplier" \
  -H "Content-Type: application/json"
echo ""

echo -e "\n${GREEN}=============================================="
echo "API Testing Complete"
echo "=============================================${NC}"
echo ""
echo "For interactive API documentation, visit:"
echo "  $BASE_URL/docs"
echo ""
