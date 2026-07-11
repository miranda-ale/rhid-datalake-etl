# RHID Datalake ETL — BHCL/Biowise

Extração periódica dos dados do RHID (ControlID) para o datalake MinIO
(`datalake-minio`, stack `datalake` no Dokploy), como backup e fonte para
futura análise de dados.

## Estrutura

- `rhid_client.py` — cliente HTTP/JWT para a API do RHID (mesmo padrão do
  `rhid-mcp`).
- `entities.py` — fetchers paginados das entidades de referência
  (colaboradores, departamentos, cargos, centros de custo, empresas,
  escalas, feriados, dispositivos).
- `storage.py` — wrapper sobre boto3/S3 para gravar objetos no MinIO.
- `daily.py` — job incremental diário (snapshot de referência + ponto do
  mês atual/anterior). Disparado pelo schedule do Dokploy.
- `backfill.py` — carga histórica única, resumível, disparada manualmente.

## Layout do bucket (`rhid-datalake`)

```
raw/colaboradores/dt=<YYYY-MM-DD>/data.json
raw/departamentos/dt=<YYYY-MM-DD>/data.json
raw/cargos/dt=<YYYY-MM-DD>/data.json
raw/centros_custo/dt=<YYYY-MM-DD>/data.json
raw/empresas/dt=<YYYY-MM-DD>/data.json
raw/escalas/dt=<YYYY-MM-DD>/data.json
raw/feriados/dt=<YYYY-MM-DD>/data.json
raw/dispositivos/dt=<YYYY-MM-DD>/data.json
raw/ponto/person_id=<id>/<YYYY-MM>.json
```

## Rodando manualmente

```bash
docker exec -it rhid-etl python backfill.py   # carga histórica (uma vez)
docker exec -it rhid-etl python daily.py      # job incremental (agendado via Dokploy)
```

## Variáveis de ambiente

Ver `env.example`.
