"""Compatibility helpers for FastMCP public test APIs."""

from __future__ import annotations

import inspect
from typing import Any

from fastmcp import FastMCP


async def _maybe_await(value: Any) -> Any:
    """Resolve sync or async FastMCP APIs uniformly."""
    if inspect.isawaitable(value):
        return await value
    return value


async def get_tool(mcp: FastMCP, name: str) -> Any:
    """Fetch a registered tool via FastMCP's public API."""
    tool = await _maybe_await(mcp.get_tool(name))
    if tool is None:
        raise AssertionError(f"Expected tool {name!r} to be registered")
    return tool


async def call_tool_fn(mcp: FastMCP, name: str, **kwargs: Any) -> Any:
    """Call a registered tool function without depending on internal managers."""
    tool = await get_tool(mcp, name)
    return await _maybe_await(tool.fn(**kwargs))


async def list_tool_names(mcp: FastMCP) -> set[str]:
    """List registered tool names across FastMCP 2 and 3."""
    if hasattr(mcp, "list_tools"):
        tools = await _maybe_await(mcp.list_tools())
        return {tool.name for tool in tools}

    tools = await _maybe_await(mcp.get_tools())
    return set(tools.keys())


async def list_resource_uris(mcp: FastMCP) -> set[str]:
    """List registered static resource URIs across FastMCP 2 and 3."""
    if hasattr(mcp, "list_resources"):
        resources = await _maybe_await(mcp.list_resources())
        return {str(resource.uri) for resource in resources}

    resources = await _maybe_await(mcp.get_resources())
    return set(resources.keys())


async def list_resource_template_uris(mcp: FastMCP) -> set[str]:
    """List registered resource template URIs across FastMCP 2 and 3."""
    if hasattr(mcp, "list_resource_templates"):
        templates = await _maybe_await(mcp.list_resource_templates())
        return {str(getattr(template, "uri", template.uri_template)) for template in templates}

    templates = await _maybe_await(mcp.get_resource_templates())
    return set(templates.keys())
