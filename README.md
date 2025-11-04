# Alfresco MCP Server

A minimal Model Context Protocol (MCP) server for Alfresco that provides a single tool to retrieve node properties via the Alfresco REST API. Built with FastMCP 2.0.

## Features

- **Single Tool**: `get_node_properties` - Retrieve properties and metadata of any Alfresco node
- **Ticket-based Authentication**: Uses Alfresco authentication tickets
- **Multiple Transport Modes**: Supports stdio, SSE, and HTTP
- **Docker Support**: Configurable container for all transport modes

## Prerequisites

- Python 3.11+
- Alfresco instance (with REST API accessible)
- Alfresco authentication ticket

## Installation

### Local Setup

1. Clone or create the project directory with all files

2. Install dependencies:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

3. Set environment variable:

```bash
export ALFRESCO_HOST=http://your-alfresco-host:8080
```

## Testing Locally with MCP Inspector

### 1. Install MCP Inspector (only once)

```bash
npm install -g @modelcontextprotocol/inspector
```

### 2. Run the server with Inspector

Start the server using `streamable-http` transport mode

```bash
python alfresco_mcp_server.py --transport http --host 127.0.0.1 --port 8003
```

Start the MCP Inspector

```bash
mcp-inspector --config ./mcp.json
```

### Getting an Alfresco Ticket

You need to authenticate with Alfresco first to get a ticket. You can do this via:

```bash
curl -X POST "http://localhost:8080/alfresco/api/-default-/public/authentication/versions/1/tickets" \
  -H "Content-Type: application/json" \
  -d '{"userId":"admin","password":"admin"}'
```

This returns a JSON response with an `id` field containing your ticket.

## Running with FastMCP Directly

### STDIO Mode (default)

```bash
python alfresco_mcp_server.py
```

### HTTP Mode

```bash
fastmcp dev alfresco_mcp_server.py --transport http --port 8003
```

### SSE Mode

```bash
fastmcp dev alfresco_mcp_server.py --transport sse --port 8003
```

## Docker Usage

### Build the Image

```bash
docker build -t alfresco-mcp-server .
```

### Run in Different Modes

#### STDIO Mode (default)

```bash
docker run -it --rm \
  -e ALFRESCO_HOST=http://your-alfresco-host:8080 \
  alfresco-mcp-server
```

#### HTTP Mode

```bash
docker run -d --rm \
  -e ALFRESCO_HOST=http://your-alfresco-host:8080 \
  -e TRANSPORT_MODE=http \
  -e HTTP=8003 \
  -p 8003:8003 \
  alfresco-mcp-server
```

#### SSE Mode

```bash
docker run -d --rm \
  -e ALFRESCO_HOST=http://your-alfresco-host:8080 \
  -e TRANSPORT_MODE=sse \
  -e HTTP=8003 \
  -p 8003:8003 \
  alfresco-mcp-server
```

### Docker Compose Example

```yaml
services:
  alfresco-mcp:
    build: .
    environment:
      - ALFRESCO_HOST=http://alfresco:8080
      - TRANSPORT_MODE=http  # or sse, stdio
      - HTTP=8003
    ports:
      - "8003:8003"  # Only needed for http/sse modes
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ALFRESCO_HOST` | Base URL of Alfresco instance | `http://localhost:8080` |
| `TRANSPORT_MODE` | Transport mode (stdio/http/sse) | `stdio` |
| `HTTP` | Port for HTTP/SSE modes | `8003` |