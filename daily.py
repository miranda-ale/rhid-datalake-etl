"""
Job incremental diário do datalake RHID.

Disparado pelo schedule do Dokploy (`scheduleType: compose`, cron diário de
madrugada). Faz duas coisas:

1. Grava um snapshot do dia de cada entidade de referência em
   `raw/<entidade>/dt=<YYYY-MM-DD>/data.json` — arquivo novo por dia, dando o
   efeito de backup/auditoria.
2. Para cada colaborador ativo, busca a apuração de ponto do mês atual e do
   mês anterior (janela de correção, cobre lançamentos retroativos) e
   sobrescreve `raw/ponto/person_id=<id>/<YYYY-MM>.json`.
"""

from __future__ import annotations

import asyncio
import calendar
import logging
from datetime import date

import entities
import storage
from rhid_client import rhid

logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("daily")

CALL_DELAY_SECONDS = 0.3

REFERENCE_ENTITIES = {
    "colaboradores": entities.fetch_colaboradores,
    "departamentos": entities.fetch_departamentos,
    "cargos": entities.fetch_cargos,
    "centros_custo": entities.fetch_centros_custo,
    "empresas": entities.fetch_empresas,
    "escalas": entities.fetch_escalas,
    "feriados": entities.fetch_feriados,
    "dispositivos": entities.fetch_dispositivos,
}


def _month_bounds(year: int, month: int, today: date) -> tuple[str, str]:
    start = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    end = date(year, month, last_day)
    if end > today:
        end = today
    return start.isoformat(), end.isoformat()


def _previous_month(year: int, month: int) -> tuple[int, int]:
    return (year - 1, 12) if month == 1 else (year, month - 1)


async def _fetch_ponto_month(person_id: int, year: int, month: int, today: date) -> None:
    data_ini, data_final = _month_bounds(year, month, today)
    key = f"raw/ponto/person_id={person_id}/{year:04d}-{month:02d}.json"
    try:
        result = await rhid.get(
            "/apuracao_ponto",
            params={"idPerson": person_id, "dataIni": data_ini, "dataFinal": data_final},
        )
    except Exception:
        log.exception(
            "Falha ao buscar ponto de person_id=%s (%s a %s)", person_id, data_ini, data_final
        )
        return
    storage.put_json(key, result)
    await asyncio.sleep(CALL_DELAY_SECONDS)


async def _snapshot_reference_entities(dt: str) -> list[dict]:
    colaboradores: list[dict] = []
    for name, fetch in REFERENCE_ENTITIES.items():
        log.info("Snapshot de %s", name)
        try:
            records = await fetch()
        except Exception:
            log.exception("Falha ao buscar %s — pulando snapshot do dia", name)
            continue
        storage.put_json(f"raw/{name}/dt={dt}/data.json", records)
        if name == "colaboradores":
            colaboradores = records
        await asyncio.sleep(CALL_DELAY_SECONDS)
    return colaboradores


async def main() -> None:
    storage.ensure_bucket()

    today = date.today()
    dt = today.isoformat()

    colaboradores = await _snapshot_reference_entities(dt)

    ativos = [c for c in colaboradores if c.get("status") == 1]
    log.info("Atualizando ponto de %d colaboradores ativos", len(ativos))

    prev_year, prev_month = _previous_month(today.year, today.month)
    for person in ativos:
        person_id = person.get("id")
        if person_id is None:
            continue
        await _fetch_ponto_month(person_id, prev_year, prev_month, today)
        await _fetch_ponto_month(person_id, today.year, today.month, today)

    log.info("Job diário concluído.")


if __name__ == "__main__":
    asyncio.run(main())
