#!/bin/bash
# Test script for the memory chat endpoint
# Usage: bash test_memory.sh

BASE_URL="${1:-http://localhost:8000}"

echo "=== Test 1: No memory, fresh question ==="
curl -s -X POST "$BASE_URL/api/chat/memory" \
  -H "Content-Type: application/json" \
  -d '{"message": "Wat is de AI Act en wanneer gaat het in?", "use_memory": false}' | python3 -m json.tool

echo ""
echo "=== Test 2: With memory, fresh session ==="
RESPONSE=$(curl -s -X POST "$BASE_URL/api/chat/memory" \
  -H "Content-Type: application/json" \
  -d '{"message": "Wat is de AI Act en wanneer gaat het in?", "use_memory": true}')
echo "$RESPONSE" | python3 -m json.tool

SESSION_ID=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('session_id',''))" 2>/dev/null)
echo ""
echo "Session ID: $SESSION_ID"

if [ -n "$SESSION_ID" ]; then
  echo ""
  echo "=== Test 3: Follow-up with memory ==="
  curl -s -X POST "$BASE_URL/api/chat/memory" \
    -H "Content-Type: application/json" \
    -d "{\"message\": \"Is de AI Act al definitief?\", \"session_id\": \"$SESSION_ID\", \"use_memory\": true}" | python3 -m json.tool
fi

echo ""
echo "=== Test 4: Same question via old structured endpoint (baseline) ==="
curl -s -X POST "$BASE_URL/api/chat/structured" \
  -H "Content-Type: application/json" \
  -d '{"message": "Wat is de AI Act en wanneer gaat het in?", "context": {"role": "other"}}' | python3 -c "
import sys, json
data = json.load(sys.stdin)
print('Answer:', data.get('main_answer', data.get('error_message', 'NO ANSWER'))[:500])
"
