FROM python:3.9-slim

# Sätt arbetskatalog
WORKDIR /app

# Kopiera requirements och installera dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopiera applikationskod
COPY . .

# Exponera port
EXPOSE 5000

# Sätt miljövariabler
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:5000/health || exit 1

# Starta applikationen
CMD ["python", "app.py"] 