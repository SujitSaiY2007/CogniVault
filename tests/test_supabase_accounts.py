from app.agent_os.supabase_accounts import SupabaseAuth, SupabaseUserMaterials


class FakeStore:
    def __init__(self):
        self.calls = []
        self.rows = []

    def select(self, table, *, params):
        self.calls.append(("select", table, params))
        return self.rows

    def insert(self, table, rows, *, upsert=False):
        self.calls.append(("insert", table, rows, upsert))
        return rows

    def delete(self, table, *, params):
        self.calls.append(("delete", table, params))

    def remove_private(self, paths):
        self.calls.append(("remove_private", paths))


def test_private_evidence_search_is_owner_scoped():
    store = FakeStore()
    store.rows = [{
        "evidence_id": "src_abc:e00001", "source_id": "src_abc",
        "modality": "pdf", "evidence_text": "Newton second law force mass acceleration",
        "location": {"page": 4}, "evidence_type": "text", "metadata": {},
    }]
    materials = SupabaseUserMaterials(store)
    results = materials.search_evidence("user_alice", "Newton acceleration", limit=3)
    assert len(results) == 1
    assert results[0]["evidence_id"] == "src_abc:e00001"
    call = store.calls[0]
    assert call[1] == "user_evidence"
    assert call[2]["owner_id"] == "eq.user_alice"
    assert call[2]["limit"] == "5000"


def test_source_delete_requires_owner_match():
    store = FakeStore()
    store.rows = [{
        "source_id": "src_abc", "owner_id": "user_alice",
        "storage_path": "user_alice/src_abc/notes.pdf",
    }]
    materials = SupabaseUserMaterials(store)
    assert materials.delete_source("user_alice", "src_abc") is True
    delete_call = next(call for call in store.calls if call[0] == "delete")
    assert delete_call[1] == "user_sources"
    assert delete_call[2]["owner_id"] == "eq.user_alice"
    assert delete_call[2]["source_id"] == "eq.src_abc"
    assert ("remove_private", ["user_alice/src_abc/notes.pdf"]) in store.calls


def test_session_token_storage_uses_digest_and_expiry():
    store = FakeStore()
    auth = SupabaseAuth(store)
    auth.issue_session("opaque-secret-token", "alice", "user_alice")
    insert_call = next(call for call in store.calls if call[0] == "insert")
    assert insert_call[1] == "cognivault_sessions"
    row = insert_call[2][0]
    import hashlib
    assert row["token_hash"] == hashlib.sha256(b"opaque-secret-token").hexdigest()
    assert "opaque-secret-token" not in row["token_hash"]
    assert row["username"] == "alice"
    assert row["expires_at"]
