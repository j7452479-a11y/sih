"""
Tests for FastAPI Server Endpoints and Web Interfaces.
"""

import pytest
from fastapi.testclient import TestClient

from c2_interface.server import app

def test_api_status_endpoint():
    client = TestClient(app)
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "OPERATIONAL"
    assert data["foveated_mls_ram_mb"] < 15.0
    assert data["ram_reduction_percent"] > 99.0

def test_api_tracks_and_cot_endpoints():
    client = TestClient(app)
    # /api/tracks
    resp_tracks = client.get("/api/tracks")
    assert resp_tracks.status_code == 200
    assert isinstance(resp_tracks.json(), list)

    # /api/cot
    resp_cot = client.get("/api/cot")
    assert resp_cot.status_code == 200

def test_c2_and_soldier_html_endpoints():
    client = TestClient(app)
    # /c2
    resp_c2 = client.get("/c2")
    assert resp_c2.status_code == 200
    assert "COMMANDER C2 TACTICAL STATION" in resp_c2.text

    # /soldier
    resp_soldier = client.get("/soldier")
    assert resp_soldier.status_code == 200
    assert "ATAK SOLDIER EUD" in resp_soldier.text

def test_structure_designation_rest_endpoints():
    client = TestClient(app)
    # 1. Initially designated structure should be null or dict
    resp_init = client.get("/api/designated_structure")
    assert resp_init.status_code == 200

    # 2. Designate a building
    sample_bld = {
        "id": "BLD-NW-01",
        "name": "Outpost Depot (Sector NW)",
        "type": "Reinforced Concrete Building",
        "x": -25.0,
        "y": 15.0,
        "width": 12.0,
        "length": 10.0,
        "height": 6.5,
        "sector": "Sector NW",
        "clearance": None
    }
    resp_post = client.post("/api/designate_structure", json={"structure": sample_bld})
    assert resp_post.status_code == 200
    data = resp_post.json()
    assert data["status"] == "SUCCESS"
    assert data["designated_structure"]["id"] == "BLD-NW-01"
    assert data["designated_structure"]["length"] == 10.0
    assert data["designated_structure"]["width"] == 12.0

    # 3. Query designated structure
    resp_get = client.get("/api/designated_structure")
    assert resp_get.status_code == 200
    assert resp_get.json()["designated_structure"]["id"] == "BLD-NW-01"

    # 4. Clear designation
    resp_clear = client.post("/api/designate_structure", json={"structure": None})
    assert resp_clear.status_code == 200
    assert resp_clear.json()["designated_structure"] is None

