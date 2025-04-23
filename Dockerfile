# Dockerfile
# dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_APP=run.py
ENV ENCRYPTION_KEY='84-7WpbNp9Y2h5aDQ-jqphkcZ7Uj3d5I4C5b09vrm9U='

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "run:app"]
