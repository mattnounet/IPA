FROM python:3.11-slim

# Installation d'eSpeak-NG (paquet système)
RUN apt-get update && \
    apt-get install -y --no-install-recommends espeak-ng && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 8080

# gunicorn = serveur de production, plus robuste que le serveur de dev Flask
CMD ["gunicorn", "-b", "0.0.0.0:8080", "-w", "2", "--timeout", "30", "app:app"]
