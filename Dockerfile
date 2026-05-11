FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# comments.db lives on a persistent disk mounted at /data
ENV COMMENTS_DB_PATH=/data/comments.db

EXPOSE 8080

CMD ["streamlit", "run", "app.py", \
     "--server.port=8080", \
     "--server.headless=true", \
     "--server.enableCORS=false"]
