# Use an official Python runtime as a parent image
FROM python:3.13-slim

# Set the working directory in the container
# Prevent Python from writing .pyc files
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Install system dependencies, including SSL certificates
RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*

# Install uv, the package manager
RUN pip install uv

# Create a virtual environment
RUN uv venv

# Copy project definition and lock file
COPY pyproject.toml uv.lock ./

# Install dependencies
# This layer is cached as long as the lock file doesn't change
RUN . .venv/bin/activate && uv pip install --no-cache-dir -e .[dev]

# Copy the rest of the application source code
COPY . .

# Ensure the data directory exists and set permissions
RUN mkdir -p /app/data && chown -R nobody:nogroup /app/data

# Run the database initialization script
RUN . .venv/bin/activate && python init_db.py

# Expose the port the app runs on
EXPOSE 8101

# Switch to a non-root user
USER nobody

# Command to run the application using Gunicorn
# This is the production server command
CMD [".venv/bin/gunicorn", "--bind", "0.0.0.0:8101", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "app:create_app()"]