import asyncio
import json
import zipfile

import pytest

from openra_env.platform_catalog import available_mods, discover_maps
from openra_env.platform_events import AgentEventHub, compact_payload


def test_discovers_packaged_and_campaign_maps(tmp_path):
    maps = tmp_path / "mods" / "ra" / "maps"
    maps.mkdir(parents=True)
    with zipfile.ZipFile(maps / "arena.oramap", "w") as archive:
        archive.writestr(
            "map.yaml",
            "Title: Arena Prime\nAuthor: Test\nCategories: [Conquest]\nPlayers:\n  PlayerReference@Multi0: {}\n  PlayerReference@Multi1: {}\n",
        )
    campaign = maps / "rescue-mission"
    campaign.mkdir()
    (campaign / "map.yaml").write_text("Title: Rescue Mission\n", encoding="utf-8")

    assert available_mods(tmp_path) == ["ra"]
    assert discover_maps(tmp_path) == [{
        "map_name": "arena.oramap",
        "title": "Arena Prime",
        "author": "Test",
        "categories": ["Conquest"],
        "players": 2,
        "bounds": "",
        "kind": "skirmish",
        "mod": "ra",
    }]
    all_maps = discover_maps(tmp_path, include_campaigns=True)
    assert [item["map_name"] for item in all_maps] == ["arena.oramap", "rescue-mission"]


def test_rejects_unknown_mod(tmp_path):
    with pytest.raises(ValueError, match="Unsupported mod"):
        discover_maps(tmp_path, "unknown")


def test_compact_payload_redacts_and_omits_large_fields():
    result = compact_payload({
        "api_key": "secret-value",
        "spatial_map": "huge",
        "message": "x" * 1200,
    })
    assert result["api_key"] == "<redacted>"
    assert result["spatial_map"] == "<large field omitted>"
    assert result["message"].endswith("...")


@pytest.mark.asyncio
async def test_event_hub_replays_and_streams_events():
    hub = AgentEventHub(max_events=2)
    hub.publish({"event": "one"})
    hub.publish({"event": "two"})
    hub.publish({"event": "three"})
    assert [event["event"] for event in hub.recent()] == ["two", "three"]

    queue = hub.subscribe()
    published = hub.publish({"event": "four", "token": "hidden"})
    delivered = await asyncio.wait_for(queue.get(), timeout=1)
    assert delivered == published
    assert delivered["token"] == "<redacted>"
    hub.unsubscribe(queue)


@pytest.mark.asyncio
async def test_external_read_helpers_use_enabled_game_state_tool(monkeypatch):
    from openra_env import mcp_server

    state = {
        "own_units": 1,
        "own_buildings": 1,
        "economy": {"cash": 5000},
        "units_summary": [{"id": 10, "type": "mcv"}],
        "buildings_summary": [{"id": 11, "type": "fact"}],
        "enemy_summary": [{"id": 20, "type": "e1"}],
        "enemy_buildings_summary": [{"id": 21, "type": "powr"}],
        "production_items": ["e1@20%"],
        "available_production": ["e1"],
    }

    event_tools = []

    async def fake_call(name, **kwargs):
        assert name == "get_game_state"
        event_tools.append(kwargs.get("event_tool"))
        return state

    monkeypatch.setattr(mcp_server, "_call", fake_call)
    assert json.loads(await mcp_server.get_units())["units"][0]["type"] == "mcv"
    assert json.loads(await mcp_server.get_buildings())["buildings"][0]["type"] == "fact"
    assert json.loads(await mcp_server.get_enemies())["buildings"][0]["type"] == "powr"
    assert json.loads(await mcp_server.get_production())["available"] == ["e1"]
    assert event_tools == ["get_units", "get_buildings", "get_enemies", "get_production"]
