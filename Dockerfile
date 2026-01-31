FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y rtl-sdr multimon-ng && rm -rf /var/lib/apt/lists/*

RUN pip install flask pyproj

COPY . .

EXPOSE 5000

CMD ["python", "server.py"]
