FROM python:3.12-slim

WORKDIR /app

# 시스템 의존성 + LibreOffice (HWP 구버전 변환용)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libxml2-dev \
    libxslt-dev \
    gcc \
    libreoffice \
    libreoffice-writer \
    libuno-cppu3 \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 복사
COPY . .

# 업로드 디렉토리 생성
RUN mkdir -p /tmp/hwpconverter/uploads

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
