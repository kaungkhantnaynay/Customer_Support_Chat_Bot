FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir uv==0.12.13

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY app ./app
COPY data/knowledge_base ./data/knowledge_base
COPY data/evaluation ./data/evaluation
COPY scripts ./scripts

EXPOSE 8000

CMD ["uv", "run", "--no-sync", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

COPY alembic.ini ./alembic.ini
COPY migrations ./migrations
