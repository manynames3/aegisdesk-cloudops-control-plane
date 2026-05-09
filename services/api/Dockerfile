FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
RUN useradd --create-home --shell /usr/sbin/nologin aegisdesk \
    && mkdir -p /app/data \
    && chown -R aegisdesk:aegisdesk /app

EXPOSE 8000

USER aegisdesk

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
