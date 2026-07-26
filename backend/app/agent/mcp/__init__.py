"""MCP client integration — lets the agent call tools hosted on an MCP server.

`client` wraps the async MCP SDK for our sync worker threads; `tools` provides
`Tool`-interface adapters that forward to MCP with a local fallback.
"""
