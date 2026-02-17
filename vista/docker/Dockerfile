# Vista Ralph Sandbox Docker Image
# Based on debian:bookworm for lightweight container with dev tools

FROM debian:bookworm-slim

ARG UID=1000
ARG GID=1000
ARG NODE_VERSION=22

# Install base packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    curl \
    git \
    jq \
    openssh-client \
    python3 \
    python3-pip \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js via NodeSource
RUN curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Claude Code CLI globally
RUN npm install -g @anthropic-ai/claude-code 2>/dev/null || true

# Create user matching host UID/GID
RUN groupadd -g ${GID} user 2>/dev/null || true \
    && useradd -m -u ${UID} -g ${GID} -s /bin/bash user 2>/dev/null || true \
    && echo "user ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Set environment
ENV DEVCONTAINER=true
ENV HOME=/home/user

USER user
WORKDIR /workspace

# Keep container alive for docker exec
CMD ["sleep", "infinity"]
