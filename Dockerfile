FROM python:3.11-slim

# Install uv (Rust-based pip alternative) and curl
RUN pip install uv && apt-get update && apt-get install -y curl

# Set working directory
WORKDIR /app

# Copy script
COPY find_similar_ticker.py .
COPY config.py .

# Make it executable
RUN chmod +x find_similar_ticker.py

# Run every 24h
CMD while true; do ./find_similar_ticker.py; sleep 86400; done
