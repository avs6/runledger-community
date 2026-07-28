FROM python:3.13-slim

WORKDIR /app

# fastembed downloads ONNX cross-encoder models at runtime; cache them under /app/.cache
ENV FASTEMBED_CACHE_PATH=/app/.cache/fastembed

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 8102

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8102"]
