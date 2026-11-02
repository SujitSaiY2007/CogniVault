"""Server-only Supabase REST/Storage adapter for durable CogniVault accounts and materials.

The service-role key must never be sent to the browser. Data access helpers require
an owner_id obtained from a validated CogniVault bearer session.
"""
from __future__ import annotations

import os
from urllib.parse import quote
import httpx
from fastapi import HTTPException


class SupabaseStore:
    def __init__(self) -> None:
        self.url = os.getenv("SUPABASE_URL", "").rstrip("/")
        self.key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        if not self.url or not self.key:
            raise RuntimeError("Supabase is not configured. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.")
        self.headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
        }
        self.timeout = httpx.Timeout(15.0, connect=5.0)

    def _request(self, method: str, path: str, *, params=None, json=None, headers=None, content=None):
        try:
            response = httpx.request(
                method, f"{self.url}{path}", params=params, json=json, headers={**self.headers, **(headers or {})},
                content=content, timeout=self.timeout,
            )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=503, detail="Persistent storage is temporarily unavailable.") from exc
        if response.status_code >= 400:
            if response.status_code == 409:
                raise HTTPException(status_code=409, detail="That username is already taken.")
            # Keep provider response details out of user-visible errors and logs.
            raise HTTPException(status_code=503, detail="Persistent storage request failed.")
        if response.status_code == 204 or not response.content:
            return None
        try:
            return response.json()
        except ValueError:
            return response.content

    def select(self, table: str, *, params: dict):
        return self._request("GET", f"/rest/v1/{table}", params=params)

    def insert(self, table: str, rows, *, upsert: bool = False):
        prefer = "return=representation"
        if upsert:
            prefer += ",resolution=merge-duplicates"
        return self._request("POST", f"/rest/v1/{table}", json=rows, headers={"Prefer": prefer})

    def rpc(self, function_name: str, params: dict):
        return self._request("POST", f"/rest/v1/rpc/{function_name}", json=params)

    def delete(self, table: str, *, params: dict):
        return self._request("DELETE", f"/rest/v1/{table}", params=params, headers={"Prefer": "return=minimal"})

    def upload_private(self, path: str, data: bytes, content_type: str) -> str:
        safe_path = quote(path, safe="/")
        self._request(
            "POST", f"/storage/v1/object/user-materials/{safe_path}",
            headers={"Content-Type": content_type, "x-upsert": "false"},
            content=data,
        )
        return path

    def remove_private(self, paths: list[str]) -> None:
        if paths:
            self._request("DELETE", "/storage/v1/object/user-materials", json={"prefixes": paths})

    def download_private(self, path: str) -> bytes:
        safe_path = quote(path, safe="/")
        result = self._request("GET", f"/storage/v1/object/user-materials/{safe_path}")
        if isinstance(result, bytes):
            return result
        raise HTTPException(status_code=503, detail="Stored file could not be retrieved.")
