FROM python:3.12-slim

WORKDIR /app

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy project files
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install dependencies
RUN uv sync --no-dev

# Hugging Face Spaces expects the app to listen on $PORT (default 7860)
ENV PORT=7860
EXPOSE 7860

# Start the web server
CMD uv run litassist web --host 0.0.0.0 --port $PORT
