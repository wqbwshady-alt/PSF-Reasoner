FROM ubuntu:24.04

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Build FPocket from bundled source (no network needed)
COPY fpocket-src /tmp/fpocket
RUN cd /tmp/fpocket && make && cp bin/fpocket /usr/local/bin/ && rm -rf /tmp/fpocket

WORKDIR /app

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt --break-system-packages

COPY server.py .

EXPOSE 8080

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]
