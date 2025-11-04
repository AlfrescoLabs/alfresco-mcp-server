# Alfresco MCP Server
# Ticket-auth version
#
# Tools implemented:
# - Search: search_content, advanced_search, search_by_metadata, cmis_search
# - Core: browse_repository, upload_document, download_document, create_folder,
#         get_node_properties, update_node_properties, delete_node
# - Checkout/Checkin: checkout_document, checkin_document, cancel_checkout
# - Resource: repository_info and get_repository_info_tool
# - Prompt: search_and_analyze
#
# Auth: uses Alfresco "ticket" via query param (?alf_ticket=...) and X-Alfresco-Ticket header.
#
# Environment variables:
#   ALFRESCO_HOST       (default: http://localhost:8080)
#   ALFRESCO_TICKET     (required) e.g. TICKET_... or Bearer-like tickets
#   MCP_LOG_LEVEL       (default: INFO)
#

import argparse
import asyncio
import base64
import json
import logging
import mimetypes
import os
from io import BytesIO
from typing import Optional, Dict, Any, List

import httpx
from fastmcp import FastMCP, Context

# ---------------------- Configuration ----------------------

ALFRESCO_HOST = os.getenv("ALFRESCO_HOST", "http://localhost:8080")
# Public v1 API roots
ALF_NODES = f"{ALFRESCO_HOST}/alfresco/api/-default-/public/alfresco/versions/1/nodes"
ALF_SEARCH = f"{ALFRESCO_HOST}/alfresco/api/-default-/public/search/versions/1/search"
ALF_DISCOVERY = f"{ALFRESCO_HOST}/alfresco/api/-default-/public/alfresco/versions/1/discovery"
ALF_CMIS = f"{ALFRESCO_HOST}/alfresco/api/-default-/public/cmis/versions/1.1/browser"

ALFRESCO_TICKET = os.getenv("ALFRESCO_TICKET", "").strip()
# RUNTIME_TICKET can be set at runtime via a tool so the LLM can inject credentials
RUNTIME_TICKET = ALFRESCO_TICKET
if not ALFRESCO_TICKET:
    logging.getLogger(__name__).warning("ALFRESCO_TICKET not set. You can set it later using the set_ticket tool.")
logger = logging.getLogger("alfresco-mcp")

# ---------------------- HTTP helpers ----------------------

def _default_headers() -> Dict[str, str]:
    # Some setups accept this header; we also always append alf_ticket as a query param.
    return {"X-Alfresco-Ticket": ALFRESCO_TICKET} if ALFRESCO_TICKET else {}

def _default_params(extra: Optional[Dict[str, Any]] = None, ticket: Optional[str] = None) -> Dict[str, Any]:
    params: Dict[str, Any] = {}
    tok = ticket or RUNTIME_TICKET
    if tok:
        params["alf_ticket"] = tok
    if extra:
        params.update(extra)
    return params

def _client() -> httpx.AsyncClient:
    # Timeout generous for large downloads/uploads
    return httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=15.0), headers=_default_headers())

async def _raise_for_status(resp: httpx.Response) -> None:
    try:
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        # Try to include Alfresco error JSON if present
        detail = None
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text
        raise RuntimeError(f"HTTP {resp.status_code}: {detail}") from e

# ---------------------- Auth guard ----------------------

def _resolve_ticket(override: Optional[str]) -> Optional[str]:
    tok = (override or RUNTIME_TICKET or "").strip()
    return tok or None

def _missing_ticket_message() -> Dict[str, Any]:
    return {
        "ok": False,
        "error": "Missing authentication ticket",
        "message": (
            "This tool requires an Alfresco authentication ticket. "
            "Call set_ticket(ticket: str) once to set it for the session, "
            "or pass it explicitly via the 'alf_ticket' parameter for this call."
        ),
        "required_action": {
            "tool": "set_ticket",
            "args": {"ticket": "<your-alfresco-ticket>"}
        }
    }

def require_ticket(fn):
    from functools import wraps
    if asyncio.iscoroutinefunction(fn):
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            ticket = _resolve_ticket(kwargs.get("alf_ticket"))
            if not ticket:
                return _missing_ticket_message()
            # ensure downstream sees a non-empty ticket
            kwargs["alf_ticket"] = ticket
            return await fn(*args, **kwargs)
        return wrapper
    else:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            ticket = _resolve_ticket(kwargs.get("alf_ticket"))
            if not ticket:
                return _missing_ticket_message()
            kwargs["alf_ticket"] = ticket
            return fn(*args, **kwargs)
        return wrapper
    
# ---------------------- FastMCP instance ----------------------

mcp = FastMCP("MCP Server for Alfresco Content Services (ticket-auth)")

@mcp.tool
async def set_ticket(ticket: str, ctx: Context = None) -> Dict[str, Any]:
    """Set/replace the authentication ticket for the current server process."""
    global RUNTIME_TICKET
    RUNTIME_TICKET = ticket.strip()
    return {"ok": True}

@mcp.tool
async def set_host(host: str, ctx: Context = None) -> Dict[str, Any]:
    """Set/replace the Alfresco host base URL at runtime (e.g., https://acs.example.com)."""
    global ALFRESCO_HOST, ALF_NODES, ALF_SEARCH, ALF_DISCOVERY, ALF_CMIS
    ALFRESCO_HOST = host.rstrip("/")
    ALF_NODES = f"{ALFRESCO_HOST}/alfresco/api/-default-/public/alfresco/versions/1/nodes"
    ALF_SEARCH = f"{ALFRESCO_HOST}/alfresco/api/-default-/public/search/versions/1/search"
    ALF_DISCOVERY = f"{ALFRESCO_HOST}/alfresco/api/-default-/public/alfresco/versions/1/discovery"
    ALF_CMIS = f"{ALFRESCO_HOST}/alfresco/api/-default-/public/cmis/versions/1.1/browser"
    return {"ok": True, "host": ALFRESCO_HOST}

# ---------------------- Search tools ----------------------

@mcp.tool
@require_ticket
async def search_content(
    query: str,
    max_results: int = 25,
    node_type: str = "",
    alf_ticket: str = ""
) -> Dict[str, Any]:
    """Search content with AFTS. Returns minimal info per hit."""
    body = {
        "query": {"query": query},
        "paging": {"maxItems": max_results, "skipCount": 0}
    }
    if node_type:
        body["filterQueries"] = [{"query": f"TYPE:\"{node_type}\""}]
    async with _client() as client:
        r = await client.post(ALF_SEARCH, params=_default_params(ticket=alf_ticket), json=body)
        await _raise_for_status(r)
        data = r.json()
    # Normalize to compact list
    entries = [
        {
            "id": e["entry"]["id"],
            "name": e["entry"]["name"],
            "nodeType": e["entry"].get("nodeType"),
            "properties": e["entry"].get("properties", {}),
            "createdAt": e["entry"].get("createdAt"),
            "modifiedAt": e["entry"].get("modifiedAt"),
        }
        for e in data.get("list", {}).get("entries", [])
    ]
    return {"count": len(entries), "results": entries}

@mcp.tool
@require_ticket
async def advanced_search(
    query: str,
    sort_field: str = "cm:modified",
    sort_ascending: bool = False,
    max_results: int = 25,
    alf_ticket: str = ""
) -> Dict[str, Any]:
    """Advanced AFTS search with sorting."""
    body = {
        "query": {"query": query},
        "paging": {"maxItems": max_results, "skipCount": 0},
        "sort": [{"type": "FIELD", "field": sort_field, "ascending": sort_ascending}],
    }
    async with _client() as client:
        r = await client.post(ALF_SEARCH, params=_default_params(ticket=alf_ticket), json=body)
        await _raise_for_status(r)
        return r.json()

@mcp.tool
@require_ticket
async def search_by_metadata(
    term: str = "",
    creator: str = "",
    content_type: str = "",
    max_results: int = 25,
    alf_ticket: str = ""
) -> Dict[str, Any]:
    """Search using simple metadata filters."""
    parts = []
    if term:
        parts.append(f'TEXT:"{term}"')
    if creator:
        parts.append(f'@cm\\:creator:"{creator}"')
    if content_type:
        parts.append(f'TYPE:"{content_type}"')
    q = " AND ".join(parts) if parts else "cm:name:*"
    return await search_content(q, max_results=max_results, alf_ticket=alf_ticket)

@mcp.tool
@require_ticket
async def cmis_search(
    cmis_query: str = "SELECT * FROM cmis:document WHERE cmis:contentStreamMimeType = 'application/pdf'",
    max_results: int = 25,
    alf_ticket: str = ""
) -> Dict[str, Any]:
    """Basic CMIS Browser binding query. Returns raw JSON from repository."""
    # CMIS Browser binding expects POST with cmisaction=query at the repo scope.
    params = _default_params({
        "cmisselector": "query",
        "statement": cmis_query,
        "searchAllVersions": "true",
        "maxItems": str(max_results),
        "skipCount": "0",
    }, ticket=alf_ticket)
    async with _client() as client:
        r = await client.get(ALF_CMIS, params=params)
        await _raise_for_status(r)
        return r.json()

# ---------------------- Core tools ----------------------

@mcp.tool
@require_ticket
async def browse_repository(
    parent_id: str = "-my-",
    max_items: int = 25,
    alf_ticket: str = ""
) -> Dict[str, Any]:
    """List children for a node id (default: user's home)."""
    url = f"{ALF_NODES}/{parent_id}/children"
    params = _default_params({"maxItems": max_items}, ticket=alf_ticket)
    async with _client() as client:
        r = await client.get(url, params=params)
        await _raise_for_status(r)
        return r.json()

@mcp.tool
@require_ticket
async def upload_document(
    file_path: str = "",
    base64_content: str = "",
    parent_id: str = "-shared-",
    description: str = "",
    alf_ticket: str = ""
) -> Dict[str, Any]:
    """Upload a document to parent_id. Use file_path or base64_content."""
    if not file_path and not base64_content:
        raise ValueError("Provide file_path or base64_content")
    filename = os.path.basename(file_path) if file_path else "upload.bin"
    content_bytes: bytes
    if file_path:
        with open(file_path, "rb") as f:
            content_bytes = f.read()
    else:
        content_bytes = base64.b64decode(base64_content)

    files = {
        "filedata": (filename, BytesIO(content_bytes), mimetypes.guess_type(filename)[0] or "application/octet-stream")
    }
    data = {
        "name": filename,
        "nodeType": "cm:content",
        "autoRename": "true",
        "description": description or ""
    }
    url = f"{ALF_NODES}/{parent_id}/children"
    async with _client() as client:
        r = await client.post(url, params=_default_params(ticket=alf_ticket), data=data, files=files)
        await _raise_for_status(r)
        return r.json()

@mcp.tool
@require_ticket
async def download_document(
    node_id: str,
    save_to_disk: bool = True,
    attachment: bool = True,
    alf_ticket: str = ""
) -> Dict[str, Any]:
    """Download document content. Returns base64 if not saving to disk."""
    url = f"{ALF_NODES}/{node_id}/content"
    params = _default_params({"attachment": str(attachment).lower()}, ticket=alf_ticket)
    async with _client() as client:
        r = await client.get(url, params=params)
        await _raise_for_status(r)
        content = r.content
    if save_to_disk:
        name_info = await get_node_properties(node_id)  # type: ignore
        filename = name_info.get("entry", {}).get("name", f"{node_id}.bin")
        out_path = os.path.abspath(filename)
        with open(out_path, "wb") as f:
            f.write(content)
        return {"saved": True, "path": out_path, "bytes": len(content)}
    else:
        return {"saved": False, "base64": base64.b64encode(content).decode("utf-8")}
    
@mcp.tool
@require_ticket
async def get_markdown_content(
    node_id: str,
    alf_ticket: str = ""
) -> str:
    """
    Return the Markdown rendition of a node as plain text.
    Uses ticket-based auth injected via query param and header.
    """
    try:
        url = f"{ALF_NODES}/{node_id}/renditions/markdown/content"
        async with _client() as client:
            resp = await client.get(url, params=_default_params(ticket=alf_ticket))
            await _raise_for_status(resp)
            return resp.text
    except Exception as e:
        return f"Failed to retrieve Markdown for `{node_id}`: {str(e)}"

@mcp.tool
@require_ticket
async def create_folder(
    folder_name: str,
    parent_id: str = "-shared-",
    description: str = "",
    alf_ticket: str = ""
) -> Dict[str, Any]:
    """Create a new folder."""
    url = f"{ALF_NODES}/{parent_id}/children"
    body = {"name": folder_name, "nodeType": "cm:folder"}
    if description:
        body["properties"] = {"cm:description": description}
    async with _client() as client:
        r = await client.post(url, params=_default_params(ticket=alf_ticket), json=body)
        await _raise_for_status(r)
        return r.json()

@mcp.tool
@require_ticket
async def get_node_properties(
    node_id: str, 
    alf_ticket: str = ""
) -> Dict[str, Any]:
    """Get node metadata and properties."""
    url = f"{ALF_NODES}/{node_id}"
    params = _default_params({"include": "properties,path,allowableOperations"}, ticket=alf_ticket)
    async with _client() as client:
        r = await client.get(url, params=params)
        await _raise_for_status(r)
        return r.json()

@mcp.tool
@require_ticket
async def update_node_properties(
    node_id: str,
    name: str = "",
    title: str = "",
    description: str = "",
    author: str = "",
    alf_ticket: str = ""
) -> Dict[str, Any]:
    """Update node name and common metadata (cm:title, cm:description, cm:author)."""
    body: Dict[str, Any] = {}
    props: Dict[str, Any] = {}
    if name:
        body["name"] = name
    if title:
        props["cm:title"] = title
    if description:
        props["cm:description"] = description
    if author:
        props["cm:author"] = author
    if props:
        body["properties"] = props
    if not body:
        return {"updated": False, "message": "No fields provided"}
    url = f"{ALF_NODES}/{node_id}"
    async with _client() as client:
        r = await client.put(url, params=_default_params(ticket=alf_ticket), json=body)
        await _raise_for_status(r)
        return r.json()

@mcp.tool
@require_ticket
async def delete_node(
    node_id: str,
    permanent: bool = False,
    alf_ticket: str = ""
) -> Dict[str, Any]:
    """Delete a node. Set permanent=True to skip trashcan."""
    url = f"{ALF_NODES}/{node_id}"
    params = _default_params({"permanent": str(permanent).lower()}, ticket=alf_ticket)
    async with _client() as client:
        r = await client.delete(url, params=params)
        await _raise_for_status(r)
        return {"deleted": True, "node_id": node_id, "permanent": permanent}

# ---------------------- Checkout/Checkin ----------------------

@mcp.tool
@require_ticket
async def checkout_document(
    node_id: str,
    download_for_editing: bool = True,
    alf_ticket: str = ""
) -> Dict[str, Any]:
    """Create a working copy for a document using public REST API (checkouts)."""
    url = f"{ALF_NODES}/{node_id}/checkouts"
    async with _client() as client:
        r = await client.post(url, params=_default_params(ticket=alf_ticket))
        await _raise_for_status(r)
        data = r.json()
    result = {"workingCopy": data}
    if download_for_editing:
        # Working copy id is in entry.id
        wc_id = data.get("entry", {}).get("id", node_id)
        dl = await download_document(wc_id, save_to_disk=True, attachment=False)  # type: ignore
        result["download"] = dl
    return result

@mcp.tool
@require_ticket
async def checkin_document(
    node_id: str,
    comment: str = "",
    major_version: bool = False,
    file_path: str = "",
    new_name: str = "", 
    alf_ticket: str = ""
) -> Dict[str, Any]:
    """Check in a working copy. If file_path is provided, uploads new content."""
    url = f"{ALF_NODES}/{node_id}/checkin"
    data = {
        "majorVersion": str(major_version).lower(),
        "comment": comment or ""
    }
    files = None
    if file_path:
        filename = new_name or os.path.basename(file_path)
        with open(file_path, "rb") as f:
            content = f.read()
        files = {"filedata": (filename, BytesIO(content), mimetypes.guess_type(filename)[0] or "application/octet-stream")}
        data["name"] = filename
    async with _client() as client:
        r = await client.post(url, params=_default_params(ticket=alf_ticket), data=data, files=files)
        await _raise_for_status(r)
        return r.json()

@mcp.tool
@require_ticket
async def cancel_checkout(
    node_id: str, 
    alf_ticket: str = ""
) -> Dict[str, Any]:
    """Cancel checkout for a working copy. (Alias: cancel-checkout endpoint)."""
    # Some versions support POST /canceledit, others DELETE /checkouts. We'll try both.
    async with _client() as client:
        # Try DELETE /checkouts first
        try:
            r = await client.delete(f"{ALF_NODES}/{node_id}/checkouts", params=_default_params(ticket=alf_ticket))
            if r.status_code < 400:
                return {"canceled": True, "method": "DELETE /checkouts"}
        except Exception:
            pass
        # Fallback to POST canceledit
        r2 = await client.post(f"{ALF_NODES}/{node_id}/canceledit", params=_default_params(ticket=alf_ticket))
        await _raise_for_status(r2)
        return {"canceled": True, "method": "POST /canceledit"}

# ---------------------- Resources & Prompts ----------------------

async def _get_repository_info(
        alf_ticket: str = ""
) -> Dict[str, Any]:
    async with _client() as client:
        r = await client.get(ALF_DISCOVERY, params=_default_params(ticket=alf_ticket))
        await _raise_for_status(r)
        return r.json()

@mcp.resource(
    "alfresco://repository/info",
    description="Live Alfresco repository info (version, edition, status)"
)
async def repository_info() -> str:
    data = await _get_repository_info()
    return json.dumps(data, indent=2)

@mcp.tool
@require_ticket
async def get_repository_info_tool(alf_ticket: str = "", ctx: Context = None) -> Dict[str, Any]:
    """Get Alfresco repository information (tool form)."""
    return await _get_repository_info(alf_ticket)

# ---------------------- Main ----------------------

def main():
    parser = argparse.ArgumentParser(description="MCP Server for Alfresco (ticket-auth) 1.1.0")
    parser.add_argument("--transport", choices=["stdio", "http", "sse"], default="stdio")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="INFO")
    args = parser.parse_args()

    logging.getLogger().setLevel(getattr(logging, args.log_level, logging.INFO))
    logger.info("Starting Alfresco MCP (ticket-auth)")
    logger.info("Using host=%s", ALFRESCO_HOST)

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    elif args.transport == "http":
        mcp.run(transport="http", host=args.host, port=args.port)
    elif args.transport == "sse":
        mcp.run(transport="sse", host=args.host, port=args.port)

if __name__ == "__main__":
    main()
