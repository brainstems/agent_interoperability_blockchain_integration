# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
  apt-get install -y --no-install-recommends \
  gcc \
  python3-dev \
  && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install additional required packages
RUN pip install --no-cache-dir \
  redis \
  crewai \
  anthropic \
  pydantic

# Copy the application code
COPY . .

# Environment variables
ENV PYTHONUNBUFFERED=1

# Run the manager
CMD ["python", "-m", "manager"] 