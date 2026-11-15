# AL-AI Engine (FastAPI, port 8001). Internal service: only AL-Core calls it.
#
#   docker build -t al-ai ./ai
#   docker run --rm -p 8001:8001 al-ai
#
# The valuation model is not baked in. On first start it is downloaded from
# Hugging Face Hub into HF_HOME; mount a volume there (compose does) so later
# starts reuse it.

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/home/app/.cache/huggingface

RUN useradd --create-home --uid 1000 app

WORKDIR /app

# Dependencies first, so code changes do not reinstall them
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app

# ml/models is where a locally trained model would go (see config.model_path)
RUN mkdir -p ml/models "$HF_HOME" && chown -R app:app /app/ml /home/app

USER app

EXPOSE 8001

# /health is cheap (no model, no network), so it is safe to poll often
HEALTHCHECK --interval=30s --timeout=3s --start-period=120s --start-interval=2s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/health', timeout=2)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
