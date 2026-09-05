FROM python:3.13-slim@sha256:9d2e5553305c7c7b0097999bb17187c69b921ccd6bc9d40e4bb5ebe652c00285

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir --requirement requirements.txt \
    && pip check \
    && groupadd --gid 10001 icdasquiz \
    && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin icdasquiz

COPY --chown=10001:10001 app.py database.py descricoes.json alembic.ini ./
COPY --chown=10001:10001 migrations ./migrations
COPY --chown=10001:10001 templates ./templates
COPY --chown=10001:10001 static ./static

USER 10001:10001
EXPOSE 8000

CMD ["gunicorn", "--worker-tmp-dir", "/dev/shm", "--worker-class", "gthread", "--workers", "1", "--threads", "4", "--timeout", "30", "--graceful-timeout", "30", "--no-control-socket", "--access-logfile", "-", "--access-logformat", "%(m)s %(U)s %(s)s %(L)s", "--bind", "0.0.0.0:8000", "app:app"]
