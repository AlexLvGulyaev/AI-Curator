"""Tests for orchestrator configuration API and service."""

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.anyio
async def test_get_orchestrator_config_creates_defaults(client):
    """GET returns a default config when the table is empty."""
    async with client:
        response = await client.get("/api/v1/admin/orchestrator/config")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] is not None
        assert data["default_intent"] == "study"
        assert "deadline" in data["intent_rules"]
        assert data["intent_source_map"]["study"]["rag"] is True
        assert data["max_lms_contents"] == 12
        assert data["max_lms_deadlines"] == 5
        assert data["fallback_messages"]["no_rag_context"] is not None


@pytest.mark.anyio
async def test_update_orchestrator_config(client):
    """PUT updates the effective orchestrator configuration."""
    async with client:
        payload = {
            "max_lms_contents": 8,
            "max_lms_deadlines": 3,
            "intent_max_tokens": {
                "organizational": 400,
                "study_beginner": 500,
                "mixed": 600,
                "default": 550,
            },
        }
        response = await client.put(
            "/api/v1/admin/orchestrator/config",
            json=payload,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["max_lms_contents"] == 8
        assert data["max_lms_deadlines"] == 3
        assert data["intent_max_tokens"]["organizational"] == 400

        # Persisted
        get_response = await client.get("/api/v1/admin/orchestrator/config")
        assert get_response.status_code == 200
        assert get_response.json()["max_lms_contents"] == 8

        # Restore defaults so later tests and production state stay consistent.
        await client.put(
            "/api/v1/admin/orchestrator/config",
            json={
                "max_lms_contents": 12,
                "max_lms_deadlines": 5,
                "intent_max_tokens": {
                    "organizational": 500,
                    "study_beginner": 650,
                    "mixed": 800,
                    "default": 750,
                },
            },
        )


@pytest.mark.anyio
async def test_update_intent_rules(client):
    """Updating intent rules affects intent classification."""
    async with client:
        get_response = await client.get("/api/v1/admin/orchestrator/config")
        assert get_response.status_code == 200
        cfg = get_response.json()

        # Add a keyword to organizational intent so that the configured mixed
        # condition (is_org AND has_keyword "итоговый проект") can fire.  The UI
        # serializes conditions as lists, so the test payload uses the same shape.
        cfg["intent_rules"]["organizational"]["keywords"] = ["о чём"]
        cfg["intent_rules"]["mixed"]["conditions"] = [
            ["is_org", "has_keyword", ["итоговый проект"]],
        ]
        response = await client.put(
            "/api/v1/admin/orchestrator/config",
            json={"intent_rules": cfg["intent_rules"]},
        )
        assert response.status_code == 200

        from services.orchestrator import Orchestrator
        updated_cfg = response.json()
        assert Orchestrator.detect_intent("о чём будет итоговый проект", ocfg=updated_cfg) == "mixed"



@pytest.mark.anyio
async def test_update_invalid_intent_source_map(client):
    """PUT rejects intent_source_map with missing boolean flags."""
    async with client:
        payload = {
            "intent_source_map": {
                "study": {"lms": False, "rag": True},
            },
        }
        response = await client.put(
            "/api/v1/admin/orchestrator/config",
            json=payload,
        )
        assert response.status_code == 422


@pytest.mark.anyio
async def test_update_missing_fallback_message(client):
    """PUT rejects fallback_messages missing required keys."""
    async with client:
        payload = {
            "fallback_messages": {
                "no_lms_data": "foo",
                "no_rag_context": "bar",
            },
        }
        response = await client.put(
            "/api/v1/admin/orchestrator/config",
            json=payload,
        )
        assert response.status_code == 422


@pytest.mark.anyio
async def test_update_intent_consistency(client):
    """PUT rejects mismatch between intent_rules and intent_source_map intents."""
    async with client:
        get_response = await client.get("/api/v1/admin/orchestrator/config")
        assert get_response.status_code == 200
        cfg = get_response.json()

        # Make a copy and remove one intent from the rules map; the persisted
        # intent_source_map still contains "organizational", so the update must fail.
        rules = dict(cfg["intent_rules"])
        rules.pop("organizational")
        response = await client.put(
            "/api/v1/admin/orchestrator/config",
            json={"intent_rules": rules},
        )
        assert response.status_code == 422
