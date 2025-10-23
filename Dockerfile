FROM registry.access.redhat.com/ubi9-minimal:9.6-1754000177
LABEL maintainer="Thejaswi Manjunatha" \
      name="mcp/powervs" \
      version="0.1.0" \
      description="MCP Server for IBM PowerVS life cycle management"

ARG PYTHON_VERSION=3.11

# Install Python, build dependencies, and supervisor

RUN microdnf update -y && \
    microdnf install -y python${PYTHON_VERSION} python${PYTHON_VERSION}-devel gcc git && \
    microdnf clean all

# Set python3 to the specified version
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python${PYTHON_VERSION} 1

RUN microdnf install -y python${PYTHON_VERSION}-pip && \ 
    microdnf clean all


# Copy and install MCP Server 2
COPY ./src /app/powervs-mcp-server
WORKDIR /app/powervs-mcp-server
RUN python3 -m venv .venv && \
    .venv/bin/pip install --upgrade pip setuptools && \
    .venv/bin/pip install -r requirements.txt

WORKDIR /app

# Set permissions for non-root user
RUN chown -R 1001:0 /app && chmod -R g=u /app

EXPOSE 8002

# Create logs directory before switching user
RUN mkdir -p /app/logs && chown -R 1001:0 /app/logs && chmod -R g=u /app/logs

# Switch to non-root
USER 1001

# Default workdir (not required but cleaner)
WORKDIR /app

# Start all services
CMD ["/bin/sh", "-c", "/app/powervs-mcp-server/.venv/bin/python /app/powervs-mcp-server/powervs-mcp-server.py > /app/logs/stdout.log 2> /app/logs/stderr.log"]

