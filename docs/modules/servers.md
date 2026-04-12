# Servers

> **Maturity**: `experimental` · **Adapter**: `KennyGraphBlackboardAdapter`

Server infrastructure providing API hosting for ASI:BUILD services. Contains the Kenny Graph SSE (Server-Sent Events) streaming server for real-time graph intelligence updates and the Kenny MCP (Model Context Protocol) server for tool-based graph access. Currently a minimal module with no public API exports — servers are run as standalone processes.

## Key Classes

| Class | Description |
|-------|-------------|
| *(No public API classes exported)* | Servers run as standalone processes |

## Example Usage

```python
# Servers are run as standalone processes:
# python -m asi_build.servers.kenny_graph_server --port 8080
# python -m asi_build.servers.kenny_mcp_server --port 8081

# From client code, connect via SSE:
import httpx
async with httpx.AsyncClient() as client:
    async with client.stream("GET", "http://localhost:8080/events") as resp:
        async for line in resp.aiter_lines():
            print(line)
```

## Blackboard Integration

KennyGraphBlackboardAdapter bridges between the Kenny Graph SSE server and the cognitive blackboard, streaming graph intelligence events in real-time to connected clients.
