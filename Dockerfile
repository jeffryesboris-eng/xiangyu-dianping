FROM node:24-alpine AS frontend
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.10-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/app:/app
WORKDIR /app
COPY requirements*.txt ./
RUN pip install --no-cache-dir -r requirements-test.txt && useradd --create-home --uid 10001 appuser
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY docker/ ./docker/
COPY --from=frontend /web/dist ./frontend/dist
RUN mkdir -p /app/.local /data/uploads && chown -R appuser:appuser /app /data
USER appuser
EXPOSE 8081
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8081", "--workers", "1", "--limit-concurrency", "128"]
