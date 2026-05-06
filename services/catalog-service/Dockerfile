FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

RUN adduser --disabled-password --gecos "" appuser
COPY shared/ /app/shared/
COPY services/catalog-service/ /app/services/catalog-service/

USER appuser
EXPOSE 8002
HEALTHCHECK --interval=30s --timeout=3s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8002/health', timeout=2)"
CMD ["python", "services/catalog-service/app.py"]

