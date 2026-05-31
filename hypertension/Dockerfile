FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
COPY src/ src/
COPY evidence/ evidence/

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["hdb", "serve", "run", "--host", "0.0.0.0", "--port", "8000"]
