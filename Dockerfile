FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

ENV PORT=5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "run:app"]
