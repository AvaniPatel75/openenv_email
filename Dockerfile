FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=7860

WORKDIR /app

COPY requirements.txt ./requirements.txt
COPY server/requirements.txt ./server-requirements.txt
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -r server-requirements.txt

COPY server ./server
COPY inference.py openenv.yaml ./

EXPOSE 7860

# 🔥 FIXED CMD - use server.app:app
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"]