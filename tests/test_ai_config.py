"""Tests for AI Configuration admin endpoints."""

import pytest


@pytest.mark.anyio
async def test_active_config_is_created(client):
    async with client:
        response = await client.get("/api/v1/admin/ai-config")
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is True
        assert data["model"] == "gpt-4o-mini"


@pytest.mark.anyio
async def test_create_and_activate_config(client):
    async with client:
        create_response = await client.post(
            "/api/v1/admin/ai-config",
            json={
                "name": "Strict",
                "system_prompt": "You are a terse assistant.",
                "model": "gpt-4o-mini",
                "temperature": 0.1,
                "max_tokens": 512,
                "top_k_retrieval": 3,
            },
        )
        assert create_response.status_code == 201
        config_id = create_response.json()["id"]

        activate_response = await client.post(f"/api/v1/admin/ai-config/{config_id}/activate")
        assert activate_response.status_code == 200
        assert activate_response.json()["is_active"] is True

        active_response = await client.get("/api/v1/admin/ai-config")
        assert active_response.json()["id"] == config_id
