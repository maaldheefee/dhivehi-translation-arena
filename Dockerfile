# Use an official Python runtime as a parent image
FROM python:3.13-slim

# Set the working directory in the container
WORKDIR /app

# Prevent Python from writing .pyc files
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install uv, the package manager
RUN pip install uv

# Copy project definition and lock file
COPY pyproject.toml uv.lock ./

# Install dependencies into a virtual environment within the container
# This is a good practice even in containers
RUN uv venv
RUN . .venv/bin/activate && uv pip install -e .

# Copy the rest of the application source code
COPY . .

# Ensure the data directory exists for the SQLite database
# This is where CasaOS will mount your persistent data
RUN mkdir -p /app/data

# Run the database initialization script to create the schema if it doesn't exist
# This only runs once when the image is built
RUN . .venv/bin/activate && python init_db.py

# Expose the port Gunicorn will run on
EXPOSE 8080

# Command to run the application using Gunicorn
# This is the production server command
CMD [".venv/bin/gunicorn", "--bind", "0.0.0.0:8080", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "app:create_app()"]