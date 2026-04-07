FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]"
RUN python -m spacy download it_core_news_md

COPY . .

CMD ["uvicorn", "tiro_core.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
