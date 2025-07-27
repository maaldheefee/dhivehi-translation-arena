# Use an official Python runtime as a parent image
FROM python:3.13-slim

# Set the working directory in the container
# Prevent Python from writing .pyc files
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Install system dependencies, including SSL certificates
RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt ./

# Install dependencies
# This layer is cached as long as the requirements file doesn't change
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application source code
COPY . .

# Ensure the data directory exists and set permissions
RUN mkdir -p /app/data && chown -R nobody:nogroup /app/data

# Run the database initialization script
RUN python init_db.py

# Expose the port the app runs on
EXPOSE 8101

# Switch to a non-root user
USER nobody

# Command to run the application using Gunicorn
# This is the production server command
CMD ["gunicorn", "--bind", "0.0.0.0:8101", "--workers", "1", "wsgi:app"]