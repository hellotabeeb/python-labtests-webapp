FROM python:3.11-slim

WORKDIR /app

COPY . .

# Install git for pip install from git repositories
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

ENV PORT=5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "run:app"]
