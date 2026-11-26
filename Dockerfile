FROM python:3.15-slim

WORKDIR /app

COPY build.py ./
COPY site/ ./site/

CMD ["python", "build.py"]
