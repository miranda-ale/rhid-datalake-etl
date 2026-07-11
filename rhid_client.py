"""
Cliente HTTP para a API do RHID (ControlID).
Gerencia autenticação JWT com renovação automática a cada 4h.
"""

from __future__ import annotations

import asyncio
import os
import time
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("RHID_BASE_URL", "https://www.rhid.com.br/v2/api.svc")


class RHIDClient:
    def __init__(self) -> None:
        self._token: str | None = None
        self._token_expires_at: float = 0
        self._lock = asyncio.Lock()

    async def _ensure_token(self) -> None:
        async with self._lock:
            if time.time() >= self._token_expires_at - 300:
                await self._login()

    async def _login(self) -> None:
        payload: dict[str, str] = {
            "email": os.getenv("RHID_LOGIN", ""),
            "password": os.getenv("RHID_PASSWORD", ""),
        }
        domain = os.getenv("RHID_DOMAIN", "")
        if domain:
            payload["domain"] = domain

        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(f"{BASE_URL}/login", json=payload)

            # A API do RHID retorna HTTP 500 tanto para erros de servidor
            # quanto para credenciais inválidas, com o motivo real no corpo
            # JSON (campo "error"). Por isso o corpo é inspecionado antes de
            # raise_for_status() — do contrário a mensagem real fica
            # mascarada por um genérico "500 Internal Server Error".
            try:
                data: dict[str, Any] = r.json()
            except ValueError:
                data = {}

            if data.get("error"):
                msg = f"Falha no login RHID: {data['error']}"
                raise ValueError(msg)

            r.raise_for_status()

            self._token = data["accessToken"]
            self._token_expires_at = time.time() + (4 * 3600)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}" if self._token else ""}

    async def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        await self._ensure_token()
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(
                f"{BASE_URL}{path}",
                headers=self._headers(),
                params=params or {},
            )
            r.raise_for_status()
            return r.json()


rhid = RHIDClient()
