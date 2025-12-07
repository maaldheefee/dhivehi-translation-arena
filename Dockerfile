# syntax=docker/dockerfile:1

# ==========================================
# Stage 1: Builder
# ==========================================
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

WORKDIR /app

# Install dependencies
# We use cache mounts to speed up installing dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Copy the project into the image
COPY . /app

# Sync the project (installs the app itself)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ==========================================
# Stage 2: Final
# ==========================================
FROM python:3.13-slim-bookworm

# Create a non-root user
RUN groupadd --system --gid 999 nonroot \
    && useradd --system --gid 999 --uid 999 --create-home nonroot

WORKDIR /app

# Copy the environment from the builder stage
COPY --from=builder --chown=nonroot:nonroot /app/.venv /app/.venv
COPY --from=builder --chown=nonroot:nonroot /app /app

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"
# Ensure Python can import the src package if needed (though uv sync usually handles this)
# ENV PYTHONPATH="/app/src:${PYTHONPATH}" 

# Create data directory and set permissions
RUN mkdir -p /app/data && chown -R nonroot:nonroot /app/data

# Switch to non-root user
USER nonroot

# Expose port
EXPOSE 8101

# Set the entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

# Default command
CMD ["gunicorn", "--bind", "0.0.0.0:8101", "--workers", "1", "wsgi:app"]