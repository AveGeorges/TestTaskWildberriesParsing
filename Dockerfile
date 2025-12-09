FROM python:3.12-slim

WORKDIR /app

COPY req.txt .

RUN pip install --no-cache-dir -r req.txt

COPY src/ ./src/

RUN mkdir -p /app/output

ENTRYPOINT ["python", "-m", "src.main"]

CMD ["--help"]

