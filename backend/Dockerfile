FROM python:3.12-slim

WORKDIR /app

RUN adduser --disabled-password --gecos "" appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chown -R appuser:appuser /app && chmod +x entrypoint.sh
USER appuser

EXPOSE 8080

ENTRYPOINT ["./entrypoint.sh"]
