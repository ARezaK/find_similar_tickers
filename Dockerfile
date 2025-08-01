FROM python:3.11-slim

# Install uv (Rust-based pip alternative) and curl
RUN pip install uv && apt-get update && apt-get install -y curl

# Set working directory
WORKDIR /app

# Copy script
COPY s1_checker.py .

# Make it executable
RUN chmod +x s1_checker.py

# Run every 24h
CMD while true; do ./s1_checker.py; sleep 86400; done
