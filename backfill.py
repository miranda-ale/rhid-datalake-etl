"""
Carga histórica única do datalake RHID.

Roda manualmente uma vez (não faz parte do schedule diário): grava o
snapshot de referência e, para cada colaborador (ativo ou inativo), percorre
mês a mês desde RHID_BACKFILL_START (env var, formato YYYY-MM, padrão
2015-01) até o mês atual, buscando a apuração de ponto e gravando em
`raw/ponto/person_id=<id>/<YYYY-MM>.json`.

É idempotente/retomável: antes de cada chamada verifica se o objeto já
existe no MinIO (meses passados são imutáveis) e pula — permite interromper
e retomar sem duplicar trabalho nem estourar rate limit da API do RHID. O
mês atual é sempre buscado de novo, já que ainda está em aberto.
"""

from __future__ import annotations

import asyncio
import calendar
import logging
import os
from datetime import date

import entities
import storage
from rhid_client import rhid

logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("backfill")

CALL_DELAY_SECONDS = 0.3
BACKFILL_START = os.getenv("RHID_BACKFILL_START", "2015-01")


def _month_bounds(year: int, month: int, today: date) -> tuple[str, str]:
    start = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    end = date(year, month, last_day)
    if end > today:
        end = today
    return start.isoformat(), end.isoformat()


def _iter_months(start_year: int, start_month: int, end_year: int, end_month: int):
    year, month = start_year, start_month
    while (year, month) <= (end_year, end_month):
        yield year, month
        month += 1
        if month > 12:
            month = 1
            year += 1


async def _backfill_person(person_id: int, today: date) -> None:
    start_year, start_month = (int(x) for x in BACKFILL_START.split("-"))
    for year, month in _iter_months(start_year, start_month, today.year, today.month):
        key = f"raw/ponto/person_id={person_id}/{year:04d}-{month:02d}.json"
        is_current_month = (year, month) == (today.year, today.month)
        if not is_current_month and storage.object_exists(key):
            continue
        data_ini, data_final = _month_bounds(year, month, today)
        try:
            result = await rhid.get(
                "/apuracao_ponto",
                params={"idPerson": person_id, "dataIni": data_ini, "dataFinal": data_final},
            )
        except Exception:
            log.exception(
                "Falha ao buscar ponto de person_id=%s (%s a %s) — retome depois",
                person_id,
                data_ini,
                data_final,
            )
            continue
        storage.put_json(key, result)
        await asyncio.sleep(CALL_DELAY_SECONDS)


async def main() -> None:
    storage.ensure_bucket()

    today = date.today()
    dt = today.isoformat()

    log.info("Gravando snapshot de referência (dt=%s)", dt)
    colaboradores = await entities.fetch_colaboradores()
    storage.put_json(f"raw/colaboradores/dt={dt}/data.json", colaboradores)
    for name, fetch in (
        ("departamentos", entities.fetch_departamentos),
        ("cargos", entities.fetch_cargos),
        ("centros_custo", entities.fetch_centros_custo),
        ("empresas", entities.fetch_empresas),
        ("escalas", entities.fetch_escalas),
        ("feriados", entities.fetch_feriados),
        ("dispositivos", entities.fetch_dispositivos),
    ):
        try:
            records = await fetch()
        except Exception:
            log.exception("Falha ao buscar %s — pulando snapshot do dia", name)
            continue
        storage.put_json(f"raw/{name}/dt={dt}/data.json", records)

    log.info(
        "Iniciando backfill de ponto para %d colaboradores desde %s",
        len(colaboradores),
        BACKFILL_START,
    )
    for i, person in enumerate(colaboradores, start=1):
        person_id = person.get("id")
        if person_id is None:
            continue
        log.info("[%d/%d] person_id=%s", i, len(colaboradores), person_id)
        await _backfill_person(person_id, today)

    log.info("Backfill concluído.")


if __name__ == "__main__":
    asyncio.run(main())
