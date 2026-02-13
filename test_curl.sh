#!/bin/bash

BASE_URL="http://localhost:8000"

echo "--- Testing Hooker API (via Curl) ---"

# Health
echo "1. Checking Health..."
RESP=$(curl -s "$BASE_URL/")
echo "   Response: $RESP"

# Create Task
echo "2. Creating Task..."
TASK_RESP=$(curl -s -X POST -H "Content-Type: application/json" -d '{"title":"Bash Test Task","priority":"URGENT"}' "$BASE_URL/tasks")
echo "   Response: $TASK_RESP"
TASK_ID=$(echo $TASK_RESP | grep -o '"id":[0-9]*' | cut -d: -f2)
echo "   Task ID: $TASK_ID"

# List Tasks
echo "3. Listing Tasks..."
curl -s "$BASE_URL/tasks" | head -c 100
echo "..."

# Create Component
echo "4. Creating Component..."
COMP_RESP=$(curl -s -X POST -H "Content-Type: application/json" -d '{"part_number":"BASH-01","stock":50}' "$BASE_URL/components")
echo "   Response: $COMP_RESP"
COMP_ID=$(echo $COMP_RESP | grep -o '"id":[0-9]*' | cut -d: -f2)

# Cleanup
if [ ! -z "$TASK_ID" ]; then
    echo "5. Deleting Task $TASK_ID..."
    curl -s -X DELETE "$BASE_URL/tasks/$TASK_ID"
fi

if [ ! -z "$COMP_ID" ]; then
    echo "6. Deleting Component $COMP_ID..."
    curl -s -X DELETE "$BASE_URL/components/$COMP_ID"
fi

echo "--- Test Complete ---"
