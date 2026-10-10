FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv

COPY requirements.txt .
# CPU-only PyTorch wheel (much smaller than the CUDA build).
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install -r requirements.txt

COPY app ./app

# Run as an unprivileged user; /data/images is the only writable path
# (plus the model cache at /models).
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /data/images /models \
    && chown -R appuser /data /models
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
