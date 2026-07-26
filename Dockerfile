FROM python:3.12-slim AS builder

WORKDIR /app

# Install poetry
RUN pip install --no-cache-dir "poetry==2.2.1"

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install runtime dependencies only (no dev)
RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-interaction --no-ansi


FROM python:3.12-slim AS runner

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY fitness_assistant/ fitness_assistant/

# Expose Streamlit default port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" || exit 1

# Run Streamlit
CMD ["streamlit", "run", "fitness_assistant/streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
