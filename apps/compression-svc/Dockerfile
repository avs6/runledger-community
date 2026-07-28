FROM python:3.13-slim

WORKDIR /app

# HF model cache (mountable volume) so the LLMLingua-2 model isn't re-downloaded each start.
ENV HF_HOME=/app/.cache/huggingface

# CPU-only PyTorch first (the default wheel is the multi-GB CUDA build we don't need),
# then llmlingua + FastAPI on top of the already-satisfied torch.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# NLTK data used by some llmlingua paths (best-effort; service is fail-open without it).
RUN python -c "import nltk; nltk.download('punkt', quiet=True); nltk.download('punkt_tab', quiet=True)" || true

COPY app.py .

EXPOSE 8104

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8104"]
