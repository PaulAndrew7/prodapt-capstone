# ADR 006: HTTP for actions, Server-Sent Events for run progress

Status: Accepted  
Date: 2026-09-26

## Context

Run progress flows one way, server to browser. Browsers must reconnect and replay missed events.

## Options

- **WebSockets everywhere.** Bidirectional; more connection state; no built-in replay.
- **HTTP + SSE.** Native reconnection with `Last-Event-ID`; same-origin cookies; simple proxying.

## Decision

User actions are ordinary HTTP requests. `GET /api/v1/runs/{id}/events` streams the append-only `run_events` log (gap-free `sequence` per run); clients deduplicate by `event_id` and replay after the last sequence. Proxies must disable buffering for that route.

## Consequences

No full-duplex channel for audio.

## Revisit when

Full-duplex voice (F25) becomes a committed feature.
