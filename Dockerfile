# Disaster Relief Supply Chain Optimizer
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p backend/data/osm backend/data/satellite backend/data/events backend/data/shelters

# Initialize database and load data
RUN python scripts/init_database.py && python scripts/load_events.py

# Expose port
EXPOSE 8000

# Run the API server
CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
