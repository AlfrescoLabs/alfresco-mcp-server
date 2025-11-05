# Alfresco MCP Server

Official Docker image for the Alfresco Model Context Protocol (MCP) Server.

## What is this?

This is a Model Context Protocol server that enables AI assistants to interact with Alfresco Content Services. It provides tools for searching, creating, updating, and managing content through the Alfresco REST API.

## Quick Start

### 1. Get an Alfresco Authentication Ticket

```bash
curl -X POST "http://localhost:8080/alfresco/api/-default-/public/authentication/versions/1/tickets" \
  -H "Content-Type: application/json" \
  -d '{"userId":"admin","password":"admin"}'
```

Save the `id` field from the response - this is your ticket.

### 2. Run the Container

```bash
docker run -it --rm \
  -e ALFRESCO_HOST=http://host.docker.internal:8080 \
  -e ALFRESCO_TICKET=YOUR_TICKET_HERE \
  angelborroy/alfresco-mcp-server:latest
```

### 3. Use with Docker MCP

Add to your Docker Desktop MCP configuration and provide:
- `ALFRESCO_HOST`: URL to your Alfresco instance
- `ALFRESCO_TICKET`: Your authentication ticket (as a secret)

## Configuration

| Environment Variable | Description | Required | Default |
|---------------------|-------------|----------|---------|
| `ALFRESCO_HOST` | Alfresco instance URL | Yes | `http://localhost:8080` |
| `ALFRESCO_TICKET` | Authentication ticket | Yes | - |
| `TRANSPORT_MODE` | MCP transport mode | No | `stdio` |

## Network Access

The container needs network access to your Alfresco instance:

- **Alfresco on host machine**: Use `http://host.docker.internal:8080`
- **Alfresco in Docker network**: Use service name (e.g., `http://alfresco:8080`)

## Available Tools

- `search_nodes` - Search for content using AFTS queries
- `get_node` - Get node details by ID
- `get_node_content` - Retrieve document content
- `create_node` - Create folders and documents
- `update_node` - Update node properties
- `delete_node` - Delete or trash nodes
- `list_children` - List folder contents
- `upload_file` - Upload files
- `get_node_metadata` - Get node metadata
- `copy_node` - Copy nodes

## Links

- **Source Code**: [GitHub - AlfrescoLabs/alfresco-mcp-server](https://github.com/AlfrescoLabs/alfresco-mcp-server)
- **MCP Registry**: [Docker MCP Registry](https://github.com/docker/mcp-registry)
- **Alfresco Documentation**: [docs.alfresco.com](https://docs.alfresco.com)

## License

Apache License 2.0

## Maintainer

Angel Borroy ([@angelborroy](https://github.com/angelborroy)) for Alfresco Labs