FROM python:3.11-slim

WORKDIR /app

# System dependencies for TA-Lib and ML
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ src/
COPY config/ config/
COPY scripts/ scripts/
COPY data/ data/

# Create data directory if not exists
RUN mkdir -p data

# Environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV TRADING_MODE=paper

EXPOSE 8080

# Healthcheck — verify Python and main module importable
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=60s \
    CMD python -c "from src.config import get_settings; print('OK')" || exit 1

# Run trading system
CMD ["python", "-m", "src.main"]
