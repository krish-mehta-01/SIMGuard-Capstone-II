import copy
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from risk_engine import api
from risk_engine.engine import RiskEngine
from risk_engine.samples import build_request, load_test_frame, pick_scenarios
from risk_engine.store import Store


@pytest.fixture()
def client(engine):
    api._engine = engine
    api._scenarios = pick_scenarios(load_test_frame(), engine)
    api._tamper_backup.clear()
    return TestClient(api.app)


def run(client, key):
    req = client.get(f"/api/v1/scenarios/{key}").json()
    return client.post("/api/v1/evaluate", json=req)


def test_scenarios_produce_the_expected_tiers(client):
    assert run(client, "legitimate").json()["decision"] == "AUTO_APPROVE"
    assert run(client, "suspicious").json()["decision"] == "MANUAL_REVIEW"
    assert run(client, "attack").json()["decision"] == "AUTO_BLOCK"
    assert run(client, "blacklisted").json()["decision"] == "AUTO_BLOCK"


def test_decision_is_anchored_and_verifiable(client):
    d = run(client, "attack").json()
    assert d["entry_id"] == 0 and d["tx_hash"].startswith("0x") and d["gas_used"] > 100000
    assert len(d["reasons"]) == 8 and d["summary"]
    audit = client.get("/api/v1/audit/verify").json()
    assert audit["integrity_ok"] and audit["verified"] == 1


def test_msisdn_never_leaves_in_clear(client):
    d = run(client, "legitimate").json()
    assert "XXXX" in d["msisdn_masked"]
    assert api._scenarios["legitimate"]["msisdn"][-8:] not in str(d)


def test_tampered_telemetry_gets_401(client):
    req = client.get("/api/v1/scenarios/legitimate").json()
    req["telemetry"]["payload"]["distance_from_home_km"] += 1.0
    r = client.post("/api/v1/evaluate", json=req)
    assert r.status_code == 401 and "signature" in r.json()["reason"]


def test_replay_gets_401(client):
    req = client.get("/api/v1/scenarios/legitimate").json()
    assert client.post("/api/v1/evaluate", json=req).status_code == 200
    again = copy.deepcopy(req)
    again["request_id"] = req["request_id"] + "-again"
    assert client.post("/api/v1/evaluate", json=again).json()["reason"] == "replayed nonce"


def test_duplicate_request_id_gets_409(client):
    req = client.get("/api/v1/scenarios/legitimate").json()
    client.post("/api/v1/evaluate", json=req)
    req2 = build_request(api._scenarios["legitimate"], request_id=req["request_id"])
    assert client.post("/api/v1/evaluate", json=req2).status_code == 409


def test_invalid_payload_gets_422(client):
    assert client.post("/api/v1/evaluate", json={"msisdn": "bad"}).status_code == 422


def test_insider_edits_are_detected_and_restorable(client):
    rid = run(client, "attack").json()["request_id"]
    for mode in ("decision", "explanation", "delete"):
        client.post("/api/v1/demo/tamper", json={"request_id": rid, "mode": mode})
        assert not client.get("/api/v1/audit/verify").json()["integrity_ok"], mode
        client.post("/api/v1/demo/restore")
        assert client.get("/api/v1/audit/verify").json()["integrity_ok"], mode


def test_analyst_resolution_flow(client):
    rid = run(client, "suspicious").json()["request_id"]
    body = {"final_decision": "AUTO_BLOCK", "analyst_id": "ANL-1", "note": "Customer could not be verified."}
    assert client.post(f"/api/v1/decisions/{rid}/resolve", json=body).status_code == 200
    assert client.post(f"/api/v1/decisions/{rid}/resolve", json=body).status_code == 422          # only once
    other = run(client, "legitimate").json()["request_id"]
    assert client.post(f"/api/v1/decisions/{other}/resolve", json=body).status_code == 422        # not a review
    led = client.get("/api/v1/ledger").json()
    assert any(e["resolution"] for e in led["entries"])


def test_edge_attack_endpoints_all_reject(client):
    for kind in ("tamper_payload", "replay", "stale", "unknown_device"):
        assert client.post(f"/api/v1/demo/edge-attack/{kind}").json()["accepted"] is False


def test_fresh_database_does_not_inherit_old_audit_trail(engine):
    engine.evaluate(build_request(load_test_frame().iloc[0]))
    assert engine.chain.entry_count() == 1
    tmp = Path(tempfile.mkdtemp())
    second = RiskEngine(store=Store(tmp / "second.db"), chain=engine.chain)
    assert second.chain.entry_count() == 0 and second.audit()["integrity_ok"]
