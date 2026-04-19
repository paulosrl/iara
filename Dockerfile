# Use official Python latest stable lightweight image
FROM python:3.12-slim

# Set environment variables to prevent Python from writing .pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    tesseract-ocr \
    tesseract-ocr-por \
    poppler-utils \
    libtesseract-dev \
    curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Create a non-root user for security
RUN useradd -m appuser && chown -R appuser /app
USER appuser

# Add user bin to path early to avoid pip warnings
ENV PATH="/home/appuser/.local/bin:${PATH}"

# Copy the requirements file first to leverage Docker cache
COPY --chown=appuser:appuser requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user --no-warn-script-location -r requirements.txt

# Copy the rest of the application code
COPY --chown=appuser:appuser . .

# Expose the port Streamlit runs on
EXPOSE 8501

# Add healthcheck to monitor the application
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Run the Streamlit application
CMD ["streamlit", "run", "frontend/iara.py", "--server.port=8501", "--server.address=0.0.0.0"]
