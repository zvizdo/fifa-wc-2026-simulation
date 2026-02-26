# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
# Removed software-properties-common as it's not needed for basic builds
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt from the root directory
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the app source code
COPY . .

# Expose the port Streamlit runs on
EXPOSE 8080

# Healthcheck to ensure the container is running
HEALTHCHECK CMD curl --fail http://localhost:8080/_stcore/health

# Command to run the application
CMD ["streamlit", "run", "main.py", "--server.port=8080", "--server.address=0.0.0.0"]

# gcloud run deploy fifa-wc-2026-simulation --source . --region=us-central1 --platform=managed --min-instances=1 --session-affinity --allow-unauthenticated   
