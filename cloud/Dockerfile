FROM ubuntu:24.04

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    curl \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Build FPocket 4.2.3 from the official upstream tarball (Discngine/fpocket).
# The source is downloaded at build time with a pinned SHA-256 instead of
# being vendored in this repository (the vendored copy was gitignored and
# absent from the build context, so CI image builds were broken).
ARG FPOCKET_VERSION=4.2.3
ARG FPOCKET_SHA256=62b3da6490eeab0db488f0182150d340de2be0be23f4fd1def9d5846ce724ede
RUN curl -fsSL "https://github.com/Discngine/fpocket/archive/refs/tags/${FPOCKET_VERSION}.tar.gz" \
        -o /tmp/fpocket.tar.gz \
    && echo "${FPOCKET_SHA256}  /tmp/fpocket.tar.gz" | sha256sum -c - \
    && tar xzf /tmp/fpocket.tar.gz -C /tmp \
    && cd "/tmp/fpocket-${FPOCKET_VERSION}" \
    && make \
    && cp bin/fpocket /usr/local/bin/ \
    && rm -rf "/tmp/fpocket-${FPOCKET_VERSION}" /tmp/fpocket.tar.gz

# Run as an unprivileged user; install app deps in a venv (no PEP 668
# bypass, so system Python packages cannot be overwritten).
RUN useradd --create-home --uid 10001 appuser
WORKDIR /app

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .

USER appuser
EXPOSE 8080

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]
