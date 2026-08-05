#!/usr/bin/env bash
set -euo pipefail

API_URL="https://curator-api.alex-n8n.site/api/v1"

# Start a public demo session
demo_resp=$(curl -s -X POST "${API_URL}/demo/start")
demo_token=$(echo "$demo_resp" | python3 -c "import sys, json; print(json.load(sys.stdin)['demo_token'])")

echo "Demo token: ${demo_token}"

# Send a question
curl -s -X POST "${API_URL}/chat" \
  -H "Content-Type: application/json" \
  -H "X-Demo-Token: ${demo_token}" \
  -d '{
    "message": "Когда дедлайн по заданию PE07?",
    "role": "active_student",
    "difficulty": "beginner"
  }'
