import asyncio
import json
from types import SimpleNamespace
from pathlib import Path

import pytest

import genesis.api.routes as routes


class DummyUser:
    def __init__(self, email="tester@example.com"):
        self.email = email
        self.username = email


def test_list_minds_coerces_float_gens(tmp_path, monkeypatch):
    # Prepare a fake minds directory
    minds_dir = tmp_path

    # Minimal identity payload with plugin gen balance as float
    mind_data = {
        "identity": {
            "gmid": "G-COERCE-1",
            "name": "CoerceMind",
            "birth_timestamp": "2025-01-01T00:00:00Z",
            "status": "active",
            "is_public": True,
        },
        "state": {},
        "memory": {},
        "plugins": {
            "gen": {
                "gen": {
                    "balance": {"current_balance": 230.5}
                }
            }
        }
    }

    # Write JSON file
    file_path = minds_dir / "G-COERCE-1.json"
    file_path.write_text(json.dumps(mind_data))

    # Monkeypatch the settings used by routes to point to our tmp minds_dir
    monkeypatch.setattr(routes, 'settings', SimpleNamespace(minds_dir=minds_dir))

    # Call list_minds directly (it's async)
    results = asyncio.run(routes.list_minds(current_user=DummyUser()))

    assert len(results) == 1
    mind = results[0]
    # Ensure gens is an integer (coerced from float)
    assert isinstance(mind.gens, int)
    assert mind.gens == 230
