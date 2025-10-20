#!/bin/bash
# Smoke test for Framely-Eyes analyzer

set -e

echo "=================================================="
echo "  Framely-Eyes Smoke Test"
echo "=================================================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
API_BASE="http://localhost:8000"
VIDEO_ID="smoke_test_$(date +%s)"
TEST_VIDEO_URL="https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/360/Big_Buck_Bunny_360_10s_1MB.mp4"

# Test 1: Health Check
echo ""
echo "${YELLOW}[Test 1]${NC} Health Check"
echo "GET ${API_BASE}/health"
HEALTH_RESPONSE=$(curl -s "${API_BASE}/health")
echo "$HEALTH_RESPONSE"

# Check if healthy
if echo "$HEALTH_RESPONSE" | grep -q '"status":"healthy"'; then
    echo "${GREEN}✓ PASS${NC} - API is healthy"
else
    echo "${RED}✗ FAIL${NC} - API is not healthy"
    exit 1
fi

# Test 2: Analyze Video
echo ""
echo "${YELLOW}[Test 2]${NC} Analyze Video"
echo "POST ${API_BASE}/analyze"
ANALYZE_RESPONSE=$(curl -s -X POST "${API_BASE}/analyze" \
    -H "Content-Type: application/json" \
    -d "{\"video_id\":\"${VIDEO_ID}\",\"media_url\":\"${TEST_VIDEO_URL}\"}")
echo "$ANALYZE_RESPONSE"

# Check if job was created
if echo "$ANALYZE_RESPONSE" | grep -q '"status":"queued"'; then
    echo "${GREEN}✓ PASS${NC} - Job queued successfully"
else
    echo "${RED}✗ FAIL${NC} - Failed to queue job"
    exit 1
fi

# Test 3: Poll Status
echo ""
echo "${YELLOW}[Test 3]${NC} Poll Job Status"
MAX_WAIT=300  # 5 minutes
WAIT_TIME=0
POLL_INTERVAL=5

while [ $WAIT_TIME -lt $MAX_WAIT ]; do
    STATUS_RESPONSE=$(curl -s "${API_BASE}/status/${VIDEO_ID}")
    STATE=$(echo "$STATUS_RESPONSE" | grep -o '"state":"[^"]*"' | cut -d'"' -f4)
    
    echo "[${WAIT_TIME}s] State: ${STATE}"
    
    if [ "$STATE" = "completed" ]; then
        echo "${GREEN}✓ PASS${NC} - Job completed successfully"
        break
    elif [ "$STATE" = "failed" ]; then
        echo "${RED}✗ FAIL${NC} - Job failed"
        echo "$STATUS_RESPONSE"
        exit 1
    fi
    
    sleep $POLL_INTERVAL
    WAIT_TIME=$((WAIT_TIME + POLL_INTERVAL))
done

if [ $WAIT_TIME -ge $MAX_WAIT ]; then
    echo "${RED}✗ FAIL${NC} - Job timed out after ${MAX_WAIT}s"
    exit 1
fi

# Test 4: Get Results (VAB)
echo ""
echo "${YELLOW}[Test 4]${NC} Get Results (VAB)"
echo "GET ${API_BASE}/result/${VIDEO_ID}"
VAB_RESPONSE=$(curl -s "${API_BASE}/result/${VIDEO_ID}")

# Check VAB structure
if echo "$VAB_RESPONSE" | grep -q '"schema_version"'; then
    echo "${GREEN}✓ PASS${NC} - VAB has schema_version"
else
    echo "${RED}✗ FAIL${NC} - VAB missing schema_version"
    exit 1
fi

if echo "$VAB_RESPONSE" | grep -q '"status"'; then
    echo "${GREEN}✓ PASS${NC} - VAB has status"
else
    echo "${RED}✗ FAIL${NC} - VAB missing status"
    exit 1
fi

if echo "$VAB_RESPONSE" | grep -q '"scenes"'; then
    echo "${GREEN}✓ PASS${NC} - VAB has scenes"
else
    echo "${RED}✗ FAIL${NC} - VAB missing scenes"
    exit 1
fi

if echo "$VAB_RESPONSE" | grep -q '"shots"'; then
    echo "${GREEN}✓ PASS${NC} - VAB has shots"
else
    echo "${RED}✗ FAIL${NC} - VAB missing shots"
    exit 1
fi

# Test 5: Coverage Validation
echo ""
echo "${YELLOW}[Test 5]${NC} Coverage Validation"

# Extract coverage metrics
TEMPORAL_COV=$(echo "$VAB_RESPONSE" | grep -o '"frames_analyzed_pct":[0-9.]*' | cut -d':' -f2)
if [ -n "$TEMPORAL_COV" ]; then
    echo "Temporal coverage: ${TEMPORAL_COV}%"
    if awk "BEGIN {exit !($TEMPORAL_COV >= 99)}"; then
        echo "${GREEN}✓ PASS${NC} - Temporal coverage ≥ 99%"
    else
        echo "${YELLOW}⚠ WARN${NC} - Temporal coverage < 99%"
    fi
fi

# Save VAB for inspection
VAB_FILE="smoke_test_vab_${VIDEO_ID}.json"
echo "$VAB_RESPONSE" > "$VAB_FILE"
echo "VAB saved to: ${VAB_FILE}"

# Summary
echo ""
echo "=================================================="
echo "${GREEN}✓ All smoke tests PASSED${NC}"
echo "=================================================="
echo ""
echo "Next steps:"
echo "  1. Inspect VAB: cat ${VAB_FILE} | jq '.'"
echo "  2. Check logs: docker compose -f docker/docker-compose.yml logs api"
echo "  3. Run golden tests for full validation"
echo ""
