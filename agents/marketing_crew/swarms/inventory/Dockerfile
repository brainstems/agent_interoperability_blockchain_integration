FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir \
  redis \
  crewai \
  anthropic \
  pydantic

# Copy the rest of the application
COPY . .

# Set environment variables
ENV REDIS_HOST=redis
ENV REDIS_PORT=6379
ENV LLM_MODEL=claude-3-5-haiku-20241022
ENV PYTHONUNBUFFERED=1

# Run the worker
CMD ["python", "manager.py"] 