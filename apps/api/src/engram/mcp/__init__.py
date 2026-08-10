"""Context delivery to an external agent over MCP.

`operations` holds the protocol-independent calls and depends only on the existing services;
`server` is a thin stdio adapter that needs the optional `mcp` extra.
"""

from engram.mcp.operations import (
    analyze_change,
    get_context,
    list_context_packages,
    list_projects,
)

__all__ = [
    "analyze_change",
    "get_context",
    "list_context_packages",
    "list_projects",
]
