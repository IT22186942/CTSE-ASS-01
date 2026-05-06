FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

RUN adduser --disabled-password --gecos "" appuser
COPY shared/ /app/shared/
COPY services/order-service/ /app/services/order-service/

USER appuser
EXPOSE 8003
HEALTHCHECK --interval=30s --timeout=3s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8003/health', timeout=2)"
CMD ["python", "services/order-service/app.py"]

