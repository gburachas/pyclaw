FROM python:3.12-slim

WORKDIR /app

# Install build deps
RUN apt-get update && apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# Install pytoclaw
COPY pyproject.toml README.md ./
COPY src/ src/
RUN pip install --no-cache-dir .

# Create workspace
RUN mkdir -p /root/.pytoclaw/workspace/memory \
             /root/.pytoclaw/workspace/sessions \
             /root/.pytoclaw/workspace/skills

EXPOSE 8080

ENTRYPOINT ["pytoclaw"]
CMD ["gateway"]
