"""
Fetchers paginados para as entidades de referência do RHID.

Cada função retorna a lista completa de registros (todas as páginas
concatenadas). A API pagina no padrão DataTables: cada página vem com
`totalRecords` e uma lista de registros — na listagem de colaboradores essa
lista está na chave `records` (ver rhid-mcp/docs/manual.md). As demais
listagens seguem o mesmo padrão de paginação; como salvaguarda, também
aceitamos a chave `data` ou a resposta já vir como lista pura.
"""

from __future__ import annotations

from typing import Any

from rhid_client import rhid

PAGE_SIZE = 100


def _extract_records(response: Any) -> list[dict[str, Any]]:
    if isinstance(response, list):
        return response
    if isinstance(response, dict):
        for key in ("records", "data"):
            value = response.get(key)
            if isinstance(value, list):
                return value
    return []


def _total_records(response: Any) -> int | None:
    if isinstance(response, dict):
        total = response.get("totalRecords")
        if isinstance(total, int):
            return total
    return None


async def _fetch_all(path: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    start = 0
    while True:
        response = await rhid.get(path, params={"start": start, "length": PAGE_SIZE})
        page = _extract_records(response)
        if not page:
            break
        records.extend(page)
        start += PAGE_SIZE
        total = _total_records(response)
        if total is not None and start >= total:
            break
    return records


async def fetch_colaboradores() -> list[dict[str, Any]]:
    return await _fetch_all("/person")


async def fetch_departamentos() -> list[dict[str, Any]]:
    return await _fetch_all("/department")


async def fetch_cargos() -> list[dict[str, Any]]:
    return await _fetch_all("/personroles")


async def fetch_centros_custo() -> list[dict[str, Any]]:
    return await _fetch_all("/costcenters")


async def fetch_empresas() -> list[dict[str, Any]]:
    return await _fetch_all("/company")


async def fetch_escalas() -> list[dict[str, Any]]:
    return await _fetch_all("/customerdb/shift.svc/a_escalas")


async def fetch_feriados() -> list[dict[str, Any]]:
    return await _fetch_all("/customerdb/holiday.svc/a")


async def fetch_dispositivos() -> list[dict[str, Any]]:
    return await _fetch_all("/device")
