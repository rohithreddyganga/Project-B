FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl texlive-latex-base texlive-latex-extra texlive-fonts-recommended \
    texlive-fonts-extra && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libnspr4 libdbus-1-3 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 \
    libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 libasound2t64 \
    libatspi2.0-0 fonts-unifont \
    && rm -rf /var/lib/apt/lists/* \
    && playwright install chromium

COPY src/ src/
COPY config/ config/
RUN mkdir -p data /root/.autoapply/browser_data

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s CMD curl -f http://localhost:8000/api/health || exit 1
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
