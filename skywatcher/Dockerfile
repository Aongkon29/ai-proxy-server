# Skywatcher — deployable container image.
# Demonstrates the 'Deployability' course concept: a reproducible, portable
# deployment anyone can run with one command.
#
# Build:  docker build -t skywatcher .
# Run:    docker run --rm -e GEMINI_API_KEY=... skywatcher ask "When can I see the ISS?"

FROM python:3.12-slim

# Don't write .pyc files & flush stdout for clean logs.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system deps (none heavy required — skyfield is pure Python).
# Build the package first to leverage Docker layer caching.
COPY pyproject.toml README.md ./
COPY skywatcher ./skywatcher

# Install the package. --no-cache-dir keeps the image small.
RUN pip install --no-cache-dir .

# Default location cache dir (writable).
RUN mkdir -p /app/.cache
ENV DEFAULT_LAT=40.014984 \
    DEFAULT_LON=-105.270546

# The CLI is the entrypoint, so you can do:
#   docker run --rm -e GEMINI_API_KEY=... skywatcher ask "..."
#   docker run --rm -e GEMINI_API_KEY=... skywatcher passes "ISS" --lat 40 --lon -105
ENTRYPOINT ["skywatcher"]
CMD ["--help"]
