# Taxora API. Built by Render from backend/ (see render.yaml); also runs anywhere Docker does.
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY alembic.ini start.sh ./
COPY migrations ./migrations
COPY app ./app

RUN useradd --create-home --uid 10001 taxora
USER taxora

EXPOSE 8000
CMD ["sh", "start.sh"]
