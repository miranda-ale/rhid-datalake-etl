# ============================================================
# RHID Datalake ETL — BHCL / Biowise
# Build de produção seguindo boas práticas Docker/OCI
# ============================================================

# ── Stage 1: dependências (cache otimizado) ──────────────────
FROM python:3.13-slim AS deps

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --target=/app/deps -r requirements.txt

# ── Stage 2: imagem final ────────────────────────────────────
FROM python:3.13-slim

LABEL org.opencontainers.image.title="RHID Datalake ETL"
LABEL org.opencontainers.image.description="Extração periódica do RHID (ControlID) para o datalake MinIO — BHCL/Biowise"
LABEL org.opencontainers.image.vendor="BHCL"
LABEL org.opencontainers.image.source="https://github.com/miranda-ale/rhid-datalake-etl"
LABEL org.opencontainers.image.version="1.0.0"

# Segurança: usuário não-root
RUN groupadd --gid 1000 etl \
    && useradd --uid 1000 --gid etl --shell /bin/sh --create-home etl

WORKDIR /app

# Copiar dependências do stage anterior (cache preservado)
COPY --from=deps /app/deps /app/deps
ENV PYTHONPATH=/app/deps

# Copiar código da aplicação
COPY --chown=etl:etl . .

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

USER etl

# Container fica ocioso — os jobs (daily.py / backfill.py) são disparados
# via `docker exec` pelo agendador do Dokploy (schedule.create, scheduleType
# "compose"), não por um processo daemon.
ENTRYPOINT ["sleep", "infinity"]
