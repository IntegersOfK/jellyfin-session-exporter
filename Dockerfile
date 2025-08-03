FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY jellyfin_session_exporter.py .

EXPOSE 9789

HEALTHCHECK --interval=30s --timeout=3s \
    CMD curl -f http://localhost:9789/metrics || exit 1

CMD ["gunicorn", "--bind", "0.0.0.0:9789", "--workers", "2", "jellyfin_session_exporter:app"]