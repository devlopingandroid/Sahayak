FROM python:3.11-slim AS models
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libglib2.0-0 libgl1 \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir 'ultralytics>=8.3,<9' 'onnx>=1.16,<1.20'
COPY sahayak_cloud/download_models.py /app/sahayak_cloud/
COPY deploy/export_object_model.py /app/deploy/
RUN python sahayak_cloud/download_models.py && python deploy/export_object_model.py

FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    SAHAYAK_CLOUD=1 SAHAYAK_DATA=/data PORT=5000 TZ=Asia/Kolkata \
    OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
RUN apt-get update && apt-get install -y --no-install-recommends libglib2.0-0 tzdata \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY deploy/requirements-cloud.txt /tmp/requirements-cloud.txt
RUN pip install --no-cache-dir -r /tmp/requirements-cloud.txt
# Explicit source-only copies keep local credentials and photos out of the image.
COPY sahayak_cloud/app.py sahayak_cloud/store.py sahayak_cloud/vision.py \
    sahayak_cloud/audio.py sahayak_cloud/conversation.py sahayak_cloud/enrollment.py \
    sahayak_cloud/server.py sahayak_cloud/objects_onnx.py /app/sahayak_cloud/
COPY --from=models /app/sahayak_cloud/models /app/sahayak_cloud/models
RUN useradd --create-home --uid 1000 sahayak && mkdir /data && chown sahayak:sahayak /data
USER sahayak
EXPOSE 5000
HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/api/health',timeout=3)"
CMD ["python", "sahayak_cloud/server.py"]
