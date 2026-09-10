FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONUTF8=1
WORKDIR /app
COPY html_web_app/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY html_web_app ./html_web_app
COPY render.yaml ./render.yaml
ENV DATA_DIR=/data FLASK_ENV=production MAX_CONTENT_MB=16
RUN mkdir -p /data
EXPOSE 8000
CMD ["waitress-serve", "--listen=0.0.0.0:8000", "html_web_app.app:app"]
