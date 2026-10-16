FROM --platform=linux/amd64 python:3.11-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py .
COPY excelqa ./excelqa
ENTRYPOINT ["python", "main.py"]