# Add Health Endpoint to FastMCP Server

Add this health endpoint to your FastMCP server (in your HTTP server file):

```python
@mcp_app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "service": config.SERVER_NAME,
        "timestamp": asyncio.get_event_loop().time()
    }
```

Add this import at the top if not already present:
```python
import asyncio
```

This should be added near your other route definitions, before the `main()` function.

Alternatively, if you want a simpler non-async version:
```python
@mcp_app.get("/health")
def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "service": config.SERVER_NAME
    }
```
