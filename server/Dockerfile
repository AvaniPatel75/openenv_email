FROM python:3.11-slim
WORKDIR /code
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY *.py ./
COPY static ./static
EXPOSE 7860
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]