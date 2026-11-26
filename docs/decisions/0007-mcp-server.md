# 0007. MCP server with the official Python SDK, in-process, local HTTP

- Status: Accepted (official SDK selected by the owner); transport details Proposed
- Date: 2026-11-26
- Related: [MCP](../architecture/mcp.md), [ADR 0001](0001-headless-backend-authority.md)

## Context

GEstimator implements MCP Streamable HTTP by hand on Python's `http.server`
with bearer authentication, serialized execution on the owner thread, revision
guards and consolidated tools. The brief selects the official Python MCP SDK
and requires that GUI and MCP never hold separate writable project copies.

## Decision

- Use the official `mcp` Python SDK for protocol handling and the Streamable
  HTTP transport, served on `127.0.0.1` from a thread inside the backend
  sidecar.
- Keep GEstimator's policies on top: off by default, token authentication,
  Host/Origin checks, read-only vs read-write modes, `if_revision`, preview,
  batch, structured envelopes, skills as resources, schema size budget.
- Tool handlers call application services through the runtime owner queue.
- No standalone stdio server (it would need its own project copy); an optional
  stateless stdio-to-HTTP proxy may be added later.

## Alternatives considered

- *Reuse GEstimator's hand-written transport*: proven, fewer dependencies, but
  the brief selects the SDK and the SDK tracks protocol revisions.
- *Separate MCP process with file-based sharing*: violates the single-writer rule.

## Consequences

Adds `mcp`, `uvicorn`, `starlette`, `pydantic`, `anyio`, `httpx` to the sidecar
(measured in M5). The asyncio loop runs on its own thread and must never touch
project objects directly.

## Verification

SDK client tests (M13), atomicity and synchronization tests, `tools/list`
snapshot with size budget.
