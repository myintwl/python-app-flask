# FROM python:3.10-slim

# COPY ./requirements.txt /tmp

# RUN pip install -r /tmp/requirements.txt

# COPY src /app

# WORKDIR /app

# CMD [ "python", "pythonflask.py" ]
FROM python:3.10-slim

# Install curl and clean up in a single layer to keep image size small
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY src .

EXPOSE 5000

CMD ["python", "pythonflask.py"]