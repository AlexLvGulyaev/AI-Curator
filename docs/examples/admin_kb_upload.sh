#!/usr/bin/env bash
set -euo pipefail

API_URL="https://curator-api.alex-n8n.site/api/v1"
TOKEN="YOUR_ADMIN_TOKEN"

# Upload a new lecture to Knowledge Base
curl -s -X POST "${API_URL}/admin/kb/documents" \
  -H "Authorization: Bearer ${TOKEN}" \
  -F "title=PE08. Zero-shot и few-shot" \
  -F "document_type=lecture" \
  -F "course_id=4" \
  -F "module=Модуль 2. Работа с LLM" \
  -F "topic=Prompt Engineering" \
  -F "difficulty=beginner" \
  -F "language=ru" \
  -F "file=@pe08_zero_shot_few_shot.md"
