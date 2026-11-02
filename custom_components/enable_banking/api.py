"""Minimal Enable Banking AIS client. Never log response bodies or credentials."""
import asyncio
from pathlib import Path
import time
import jwt

class ApiError(Exception):
    def __init__(self, status):
        self.status = status
        super().__init__(f"Enable Banking HTTP {status}")

class Client:
    def __init__(self, hass, session, app_id, key_path):
        self.hass, self.session = hass, session
        self.app_id, self.key_path = app_id, key_path

    def _token(self):
        key = Path(self.key_path).read_bytes()
        now = int(time.time())
        return jwt.encode({"iss": "enablebanking.com", "aud": "api.enablebanking.com",
                           "iat": now, "exp": now + 300}, key, algorithm="RS256",
                          headers={"kid": self.app_id})

    async def request(self, method, path, **kwargs):
        try:
            token = await self.hass.async_add_executor_job(self._token)
        except jwt.PyJWTError as err:
            raise ValueError("Invalid application key") from err
        async with asyncio.timeout(60):
            async with self.session.request(method, "https://api.enablebanking.com" + path,
                    headers={"Authorization": "Bearer " + token}, **kwargs) as resp:
                if resp.status >= 400:
                    raise ApiError(resp.status)
                return await resp.json()

    async def transactions(self, uid, start, end):
        params = {"date_from": start, "date_to": end, "transaction_status": "BOOK"}
        rows, seen_keys = [], set()
        for _ in range(1000):
            data = await self.request("GET", f"/accounts/{uid}/transactions", params=params)
            rows.extend(data["transactions"])
            key = data.get("continuation_key")
            if not key:
                return rows
            if key in seen_keys:
                raise ValueError("Repeated pagination key")
            seen_keys.add(key)
            params["continuation_key"] = key
        raise ValueError("Pagination limit exceeded")
