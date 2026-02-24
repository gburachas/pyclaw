FROM python:3.12-slim

WORKDIR /app

# Install build deps
RUN apt-get update && apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# Install pyclaw
COPY pyproject.toml README.md ./
COPY src/ src/
RUN pip install --no-cache-dir .

# Create workspace
RUN mkdir -p /root/.pyclaw/workspace/memory \
             /root/.pyclaw/workspace/sessions \
             /root/.pyclaw/workspace/skills

EXPOSE 8080

ENTRYPOINT ["pyclaw"]
CMD ["gateway"]
