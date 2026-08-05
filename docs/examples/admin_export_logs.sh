#!/usr/bin/env bash
set -euo pipefail

API_URL="https://ai-curator-api.example.com/api/v1"
TOKEN="YOUR_ADMIN_TOKEN"

# Export operational logs to CSV
curl -s -X POST "${API_URL}/admin/operational-logs/export" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "date_from": "2026-08-01T00:00:00Z",
    "date_to": "2026-08-05T23:59:59Z"
  }' \
  -o operational_logs_2026-08-01_2026-08-05.csv

# Export audit log to CSV
curl -s -X POST "${API_URL}/admin/audit/export" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{}' \
  -o audit_log.csv
