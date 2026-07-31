# AI Curator — Deployment Guide

## Purpose

This document is the single Source of Truth for reproducing a fully working AI Curator instance. Follow it step by step; if the system is not functional after completing the guide, the guide is out of date.

## Prerequisites

- Linux server with Docker Engine and Docker Compose plugin installed.
- Public DNS records pointing to the server (for production with Traefik):
  - `curator.alex-n8n.site` → Web UI
  - `curator-admin.alex-n8n.site` → Admin Console
  - `curator-api.alex-n8n.site` → Backend API
  - `lms.alex-n8n.site` → Moodle LMS
- A Traefik reverse proxy on the `n8n_default` Docker network (production only). For local deployment the services expose ports internally.

## Required environment variables

Create `.env` in the repository root with at least the following variables:

```bash
# Backend
DATABASE_URL=postgresql+asyncpg://ai_curator:AICPG3hfpf2100@ai-curator-postgres:5432/ai_curator
OPENAI_API_KEY=YOUR_OPENAI_API_KEY
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_CHAT_MODEL=gpt-4o-mini-2024-07-18
CHROMA_HOST=ai-curator-chroma
CHROMA_PORT=8000

# LMS integration
LMS_BASE_URL=https://lms.alex-n8n.site
LMS_API_TOKEN=YOUR_MOODLE_WEBSERVICE_TOKEN

# Admin Console auth
ADMIN_CONSOLE_URL=https://curator-admin.alex-n8n.site
ADMIN_CONSOLE_TOKEN=YOUR_RANDOM_HEX_TOKEN_64_CHARS

# Web UI
WEB_UI_URL=https://curator.alex-n8n.site

# Log retention and archiving
ARCHIVE_DIR=/app/storage/archives
HOT_RETENTION_DAYS=30
TRACE_RETENTION_DAYS=7

# KB Content Git repository
KB_CONTENT_GIT_ENABLED=true
KB_CONTENT_REPO_PATH=/app/kb-content
# Leave empty for local-only mode, or set an SSH URL for production sync:
KB_CONTENT_REPO_URL=
KB_CONTENT_SSH_KEY_PATH=
KB_CONTENT_DEFAULT_BRANCH=main

# Moodle (only if the embedded LMS stack is used)
MOODLE_DB_USER=moodle
MOODLE_DB_PASSWORD=YOUR_MOODLE_DB_PASSWORD
MOODLE_DB_NAME=moodle
MOODLE_ADMIN_USER=admin
MOODLE_ADMIN_PASSWORD=YOUR_MOODLE_ADMIN_PASSWORD
MOODLE_ADMIN_EMAIL=admin@example.com
MOODLE_SITE_NAME=AI Curator Demo LMS
```

Never commit `.env` to the repository. It is listed in `.gitignore`.

## Build and start

From the repository root:

```bash
docker compose up --build -d
```

This builds the backend, Web UI, Admin Console images and starts:
- PostgreSQL for the backend (`ai-curator-postgres`)
- Chroma vector store (`ai-curator-chroma`)
- Moodle LMS + its own PostgreSQL (`ai-curator-lms`, `ai-curator-lms-db`)
- Backend API (`ai-curator-backend`)
- Web UI (`ai-curator-web-ui`)
- Admin Console (`ai-curator-admin-console`)

## Verify the deployment

Wait for all containers to become `healthy`:

```bash
docker compose ps
```

Check backend health:

```bash
curl -s https://curator-api.alex-n8n.site/health
```

Expected result: `{"status":"ok","service":"ai-curator-backend"}`.

## First-time setup

### 1. Seed Moodle demo data (optional, for E2E testing)

```bash
docker exec ai-curator-backend python3 /app/scripts/seed-lms-demo-data.py
```

This creates three demo student roles with different progress profiles and rebuilds the Prompt Engineering course structure.

### 2. Create an LMS API token

In Moodle:
1. Site Administration → Server → Web services → Manage tokens.
2. Create a token for a user that is enrolled or has management capability in all courses the chat must serve.
3. Put the token into `.env` as `LMS_API_TOKEN` and restart the backend.

### 3. Index Knowledge Base documents

1. Open Admin Console at `https://curator-admin.alex-n8n.site`.
2. Log in using the value of `ADMIN_CONSOLE_TOKEN`.
3. Upload course materials in the Knowledge Base section.
4. Publish documents so they become searchable.

Without published KB documents, study questions will return an out-of-scope refusal.

### 4. KB Content Git repository (optional but recommended)

By default `kb-content/` is mounted into the backend container at `/app/kb-content` and tracked as a local Git repository. This lets the backend commit every uploaded or edited KB source file and store `git_commit_hash` / `git_blob_hash` on the document version.

#### Local-only mode (development / demo)

With `KB_CONTENT_REPO_URL=` (empty) the backend initializes a local repo inside the container and commits locally. Nothing is pushed. The working copy is persisted on the Docker host via the bind mount, so commits survive container restarts.

Verify the local repo:

```bash
docker exec ai-curator-backend git -C /app/kb-content log --oneline -3
```

Expected: recent commits from document uploads, for example:

```text
a1b2c3d feat(kb): upload "CC01. Установка и первый запуск Claude Code"
01f72e9 init(kb-content): course materials for Claude Code training
```

#### Production mode with remote repository

1. Create a dedicated repository (for example `git@github.com:your-org/ai-curator-kb-content.git`).
2. Generate an SSH deploy key with **read/write** access and save the private key on the server, for example `/opt/ai-curator-kb-content-deploy.key`.
3. Set in `.env`:

```bash
KB_CONTENT_REPO_URL=git@github.com:your-org/ai-curator-kb-content.git
KB_CONTENT_SSH_KEY_PATH=/app/secrets/kb-content-deploy.key
KB_CONTENT_GIT_ENABLED=true
```

4. Mount the deploy key into the backend container by adding to `docker-compose.yml` under `ai-curator-backend.volumes`:

```yaml
- ./secrets/kb-content-deploy.key:/app/secrets/kb-content-deploy.key:ro
```

5. Make sure the key is not committed to the repository (add `secrets/` to `.gitignore`).
6. Restart the backend:

```bash
docker compose up -d ai-curator-backend
```

7. Upload or edit a KB document in Admin Console. The backend will clone/push to the remote repository and fill Git metadata on the version.

#### Verifying remote sync

```bash
docker exec ai-curator-backend git -C /app/kb-content log --oneline --decorate -3
```

If remote is configured you should see `(origin/main)` on the latest commit.

## Important deployment notes

### Chroma persistence

Chroma 0.5.x stores its SQLite database in `/data` inside the container. The Docker Compose volume is mounted there. Do **not** use `latest` for Chroma in production — the image tag is pinned to a specific digest in `docker-compose.yml`.

### LMS course access

If a course is visible to students but the service token cannot read its assignments, the backend automatically falls back to parsing deadlines from `core_course_get_contents`. This is transparent to the user.

### Traefik

Production routing relies on the external `n8n_default` Docker network. Make sure Traefik is connected to that network and that DNS records resolve to the server before issuing certificates.

## Restart after code changes

```bash
docker compose build ai-curator-backend
docker compose up -d ai-curator-backend
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ai-curator-chroma` unhealthy | Healthcheck utility missing or wrong mount | Image and healthcheck are pinned in `docker-compose.yml`. If you see `wget: not found`, pull the latest committed version. |
| Study questions return refusal after restart | Chroma volume mounted to wrong path, data lost on container recreation | Ensure `/data` mount. Re-upload and re-index documents if data was lost. |
| Course 4+ deadlines missing | Service token lacks `mod_assign_get_assignments` capability | Use the fallback behavior or enroll the token user in the course. |
| Admin Console returns 401 | `ADMIN_CONSOLE_TOKEN` mismatch | Check `.env` and restart backend. |
| `/app/storage/archives` grows too large | Logs are archived but never removed from disk | Configure logrotate or scheduled cleanup on the Docker host. |

## Validation checklist

After a fresh deployment, confirm:

- [ ] `docker compose ps` shows all services `Up` and `healthy`.
- [ ] Backend health endpoint returns `{"status":"ok"}`.
- [ ] A refusal request (`Выставь мне зачёт...`) returns `intent: refusal` and `latency_ms: 0`.
- [ ] A deadline question returns a correct due date from LMS.
- [ ] A study question returns a KB-based answer with sources.
- [ ] After uploading a KB document, `docker exec ai-curator-backend git -C /app/kb-content log --oneline -3` shows a new commit.
- [ ] The uploaded document version in Admin Console displays non-empty `git_commit_hash` and `git_blob_hash`.
