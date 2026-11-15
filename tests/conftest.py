from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import pytest
from fastapi.testclient import TestClient

from app.api import create_app
from app.config import Settings
from app.db import Database
from app.llm import LLM
from app.persistence import Backend, StorageError
from app.service import CogniVault

ROOT = Path(__file__).resolve().parent.parent


def make_service(backend: Optional[Backend] = None, llm: Optional[LLM] = None, seed: bool = True) -> CogniVault:
    settings = Settings(data_dir=ROOT / "data", seed_demo_course=seed)
    svc = CogniVault(settings, db=Database(":memory:"), llm=llm or LLM(), backend=backend)
    if seed:
        svc.seed_demo_course()
    return svc


@pytest.fixture(scope="session")
def seeded() -> CogniVault:
    """Read-only shared service with the demo course. Tests must not mutate it."""
    return make_service()


@pytest.fixture()
def fresh() -> CogniVault:
    return make_service()


class MemoryBackend(Backend):
    """Durable backend stand-in: survives across service instances like Supabase does."""

    durable = True
    name = "memory"

    def __init__(self):
        self.users: dict[str, dict[str, Any]] = {}
        self.sessions: dict[str, str] = {}
        self.files: dict[str, dict[str, dict[str, Any]]] = {}
        self.snapshots: dict[str, dict[str, Any]] = {}
        self.fail_saves = False

    def create_user(self, username, password_hash, learner_id):
        if username in self.users:
            raise StorageError("That username is already taken.")
        self.users[username] = {"username": username, "password_hash": password_hash, "learner_id": learner_id}

    def get_user(self, username):
        return self.users.get(username)

    def create_session(self, token, username):
        self.sessions[token] = username

    def resolve_session(self, token):
        u = self.sessions.get(token)
        return (u, self.users[u]["learner_id"]) if u else None

    def delete_session(self, token):
        self.sessions.pop(token, None)

    def save_file(self, owner_id, source, data, mime, evidence_rows):
        if self.fail_saves:
            raise StorageError("simulated outage")
        self.files.setdefault(owner_id, {})[source["source_id"]] = {**source, "data": data}

    def list_files(self, owner_id):
        return [{k: v for k, v in f.items() if k != "data"} for f in self.files.get(owner_id, {}).values()]

    def load_file(self, owner_id, source_id):
        f = self.files.get(owner_id, {}).get(source_id)
        return f["data"] if f else None

    def delete_file(self, owner_id, source_id):
        self.files.get(owner_id, {}).pop(source_id, None)

    def load_snapshot(self, owner_id):
        return self.snapshots.get(owner_id, {})

    def save_snapshot(self, owner_id, snapshot):
        import json

        self.snapshots[owner_id] = json.loads(json.dumps(snapshot))  # same round trip as JSONB


def client_for(svc: CogniVault) -> TestClient:
    return TestClient(create_app(svc, settings=svc.settings))


def signup(client: TestClient, username: str) -> tuple[dict[str, str], str]:
    r = client.post("/api/v1/auth/signup", json={"username": username, "password": "correct-horse-1"})
    assert r.status_code == 200, r.text
    body = r.json()
    return {"Authorization": f"Bearer {body['access_token']}"}, body["learner_id"]


NOTES = (
    b"# Thermodynamics\n\n"
    b"Temperature is a measure of the average kinetic energy of the particles in a substance.\n\n"
    b"Heat is the energy transferred between objects because of a temperature difference. "
    b"The heat needed is Q = m * c * dT, where Q is the heat in joules (J), m is the mass in kilograms (kg), "
    b"c is the specific heat capacity in joules per kilogram kelvin (J/kg K), and dT is the temperature change in kelvin (K).\n\n"
    b"# Entropy\n\n"
    b"Entropy is a measure of the number of ways the energy of a system can be arranged. "
    b"The second law of thermodynamics states that the total entropy of an isolated system never decreases. "
    b"Understanding entropy requires temperature and heat.\n"
)
