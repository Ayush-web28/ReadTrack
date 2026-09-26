# REST API image.  Build context: rest-api/
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first: this layer is cached until requirements.txt changes,
# so code edits rebuild in seconds.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# The SQLite file lives in /data, which docker-compose mounts as a volume so the
# data survives container restarts and rebuilds.
ENV DATABASE_URL=sqlite:////data/readtrack.db
RUN useradd --create-home appuser && mkdir /data && chown appuser /data
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
